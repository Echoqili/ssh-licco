from __future__ import annotations

import asyncio
import inspect
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import paramiko
from paramiko import AutoAddPolicy, HostKeys, RejectPolicy, SSHClient, WarningPolicy

from .connection_config import ConnectionConfig
from .exceptions import ConnectionException
from .executor import get_executor
from .logging_config import get_logger


class SessionState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    EXECUTING = "executing"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class SessionInfo:
    session_id: str
    host: str
    port: int
    username: str
    state: SessionState
    connected_at: datetime
    last_activity: datetime
    command_count: int = 0
    error_message: str | None = None
    last_keepalive: datetime = field(default_factory=datetime.now)


class SSHSession:
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: SSHClient | None = None
        self.session_id = str(uuid.uuid4())
        self._state = SessionState.DISCONNECTED
        self._connected_at: datetime | None = None
        self._last_activity: datetime = datetime.now()
        self._last_keepalive: datetime = datetime.now()
        self._keepalive_task: asyncio.Task | None = None
        self._executor = get_executor()
        self._connect_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._background_channels: list = []  # 保持 background channel 引用，防止 GC 关闭 channel
        self._reconnect_count = 0  # 重连次数统计
        self._max_reconnects = 3  # 最大重连次数
        self._logger = get_logger("SSHSession")

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        # 检查状态标志和实际连接状态
        if self._state != SessionState.CONNECTED or self.client is None:
            return False

        try:
            transport = self.client.get_transport()
            if transport is None or not transport.is_active():
                self._state = SessionState.DISCONNECTED
                return False
            return True
        except Exception:
            self._state = SessionState.DISCONNECTED
            return False

    async def connect(self) -> SessionInfo:
        async with self._connect_lock:
            if self.is_connected:
                return self._get_session_info()

            self._state = SessionState.CONNECTING

            try:
                await self._executor.submit(self._connect_sync, timeout=self.config.timeout + 10)
                self._connected_at = datetime.now()
                self._state = SessionState.CONNECTED
                await self._start_keepalive()
                return self._get_session_info()
            except Exception as e:
                self._state = SessionState.ERROR
                raise ConnectionError(f"Failed to connect to {self.config.host}: {str(e)}")

    def _connect_sync(self) -> None:
        self.client = SSHClient()

        # 🔒 主机密钥验证策略（修复 MITM 漏洞）
        if self.config.accept_new_host_key:
            # ⚠️ 测试模式：自动接受新主机密钥（仅用于开发/测试）
            self.client.set_missing_host_key_policy(AutoAddPolicy())
        elif self.config.strict_host_key_checking:
            # 🔒 严格模式：使用已知主机密钥文件验证
            host_keys = HostKeys()

            # 优先使用配置的 known_hosts 路径
            if self.config.known_hosts_path:
                known_hosts_file = Path(os.path.expanduser(str(self.config.known_hosts_path)))
            else:
                # 默认使用 ~/.ssh/known_hosts
                known_hosts_file = Path.home() / ".ssh" / "known_hosts"

            if known_hosts_file.exists():
                host_keys.load(str(known_hosts_file))

            self.client.get_host_keys().update(host_keys)
            self.client.set_missing_host_key_policy(RejectPolicy())
        else:
            # 宽松模式：使用警告策略
            self.client.set_missing_host_key_policy(WarningPolicy())

        connect_kwargs = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.timeout,
            "compress": self.config.compress,
            "look_for_keys": self.config.look_for_keys,
            "allow_agent": self.config.allow_agent,
        }

        if self.config.auth_method == "password" and self.config.password:
            connect_kwargs["password"] = self.config.password
        elif self.config.auth_method == "private_key" and (
            self.config.private_key_path or self.config.private_key_material
        ):
            # 加固点 2：优先使用内存私钥（密钥不落地），其次磁盘路径
            if self.config.private_key_material:
                from .clients.paramiko_client import _load_pkey_from_memory

                pkey = _load_pkey_from_memory(
                    self.config.private_key_material, self.config.passphrase
                )
                if pkey is not None:
                    connect_kwargs["pkey"] = pkey
                elif self.config.password:
                    connect_kwargs["password"] = self.config.password
                else:
                    raise SSHException("内存私钥解析失败且无 password 兜底")
            else:
                connect_kwargs["key_filename"] = str(self.config.private_key_path)
                if self.config.passphrase:
                    connect_kwargs["passphrase"] = self.config.passphrase

        self.client.connect(**connect_kwargs)  # type: ignore[arg-type]

        transport = self.client.get_transport()
        if transport:
            transport.set_keepalive(self.config.keepalive_interval)

    async def _start_keepalive(self):
        if self._keepalive_task:
            self._keepalive_task.cancel()

        async def keepalive_loop():
            while self.is_connected and not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(self.config.keepalive_interval)

                    if not self.is_connected or self._shutdown_event.is_set():
                        break

                    transport = await self._executor.submit(
                        lambda: self.client.get_transport() if self.client else None
                    )
                    if transport and transport.is_active():
                        await self._executor.submit(transport.send_ignore)
                        self._last_keepalive = datetime.now()
                    else:
                        # Transport 不再活跃，标记为断开
                        self._state = SessionState.DISCONNECTED
                        self._logger.warning(
                            f"Keepalive failed: transport not active for session {self.session_id}"
                        )
                        break
                except Exception as e:
                    self._state = SessionState.DISCONNECTED
                    self._logger.warning(f"Keepalive failed for session {self.session_id}: {e}")
                    break

        self._keepalive_task = asyncio.create_task(keepalive_loop())

    async def execute_command(
        self,
        command: str,
        timeout: int = 30,
        background: bool = False,
        stdin_data: str | None = None,
        get_pty: bool = False,
    ) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")

        async with self._connect_lock:
            self._state = SessionState.EXECUTING
            self._last_activity = datetime.now()
            start_time = asyncio.get_event_loop().time()
            heartbeat_task = None
            truncated_cmd = command[:200].replace("\n", " ")

            try:
                self._logger.info(
                    f"[cmd-start] session={self.session_id} "
                    f"host={self.config.host}:{self.config.port} "
                    f"timeout={timeout}s background={background} get_pty={get_pty} "
                    f"command={truncated_cmd}"
                )

                async def _heartbeat() -> None:
                    try:
                        elapsed = 0
                        while True:
                            await asyncio.sleep(10)
                            elapsed += 10
                            self._logger.debug(
                                f"[cmd-heartbeat] session={self.session_id} "
                                f"elapsed={elapsed}s still executing: {truncated_cmd}"
                            )
                    except asyncio.CancelledError:
                        pass

                heartbeat_task = asyncio.create_task(_heartbeat())

                result = await self._executor.submit(
                    self._execute_command_sync,
                    command,
                    timeout,
                    background,
                    stdin_data,
                    get_pty,
                    timeout=timeout + 5,
                )

                elapsed = asyncio.get_event_loop().time() - start_time
                self._logger.info(
                    f"[cmd-done] session={self.session_id} elapsed={elapsed:.1f}s "
                    f"exit_code={result.get('exit_code')} command={truncated_cmd}"
                )
                return result
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                self._logger.error(
                    f"[cmd-timeout] session={self.session_id} elapsed={elapsed:.1f}s "
                    f"timeout={timeout}s command={truncated_cmd}"
                )
                raise
            except ConnectionError:
                # 连接错误，标记为断开状态
                self._state = SessionState.DISCONNECTED
                raise
            except Exception as e:
                elapsed = asyncio.get_event_loop().time() - start_time
                self._logger.error(
                    f"[cmd-error] session={self.session_id} elapsed={elapsed:.1f}s "
                    f"error={type(e).__name__}: {e} command={truncated_cmd}"
                )
                # 其他异常也检查连接状态
                if not self.is_connected:
                    self._state = SessionState.DISCONNECTED
                    raise ConnectionError(f"SSH connection lost during command execution: {str(e)}")
                raise
            finally:
                if heartbeat_task is not None:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                if self.is_connected:
                    self._state = SessionState.CONNECTED

    def _execute_command_sync(
        self,
        command: str,
        timeout: int,
        background: bool = False,
        stdin_data: str | None = None,
        get_pty: bool = False,
    ) -> dict:
        assert self.client is not None

        # get_pty=True 时分配伪终端，sudo -S 在 requiretty 配置下需要
        # 注意：get_pty=True 会将 stderr 合并到 stdout，stderr channel 为空
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout, get_pty=get_pty)

        # 通过 stdin 传递数据（如 sudo 密码），避免出现在进程列表中
        if stdin_data is not None and not background:
            stdin.write(stdin_data)
            stdin.flush()
            stdin.channel.shutdown_write()

        if background:
            # Keep channel references alive to prevent GC from closing the
            # channel while the background process is still starting up.
            # The channel will be cleaned up when the session disconnects.
            self._background_channels.append((stdin, stdout, stderr))
            # Limit stored channels to prevent memory leak
            if len(self._background_channels) > 10:
                self._background_channels = self._background_channels[-5:]

            try:
                pid = stdout.channel.pid  # type: ignore[attr-defined]
                pid_msg = f"PID: {pid}"
            except AttributeError:
                pid_msg = "background mode"

            return {
                "exit_code": 0,
                "stdout": f"Command started in {pid_msg}",
                "stderr": "",
                "session_id": self.session_id,
            }

        exit_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode("utf-8", errors="replace")
        stderr_data = stderr.read().decode("utf-8", errors="replace")

        return {
            "exit_code": exit_code,
            "stdout": stdout_data,
            "stderr": stderr_data,
            "session_id": self.session_id,
        }

    async def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")

        async with self._connect_lock:
            self._state = SessionState.EXECUTING
            self._last_activity = datetime.now()
            try:
                loop = asyncio.get_event_loop()
                stream = await loop.run_in_executor(
                    self._executor.executor, self._execute_command_stream_sync, command
                )
                async for line in self._async_stream_wrapper(stream):
                    yield line
            finally:
                self._state = SessionState.CONNECTED

    def _execute_command_stream_sync(self, command: str) -> Iterator[str]:
        assert self.client is not None

        stdin, stdout, stderr = self.client.exec_command(command)

        for line in stdout:
            yield line.decode("utf-8", errors="replace")

    async def _async_stream_wrapper(self, sync_iterator):
        loop = asyncio.get_event_loop()
        while True:
            try:
                item = await loop.run_in_executor(
                    self._executor.executor, lambda: next(sync_iterator, None)
                )
                if item is None:
                    break
                yield item
            except StopIteration:
                break

    async def open_shell(
        self, term: str = "xterm", width: int = 80, height: int = 24
    ) -> paramiko.Channel:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")

        self._last_activity = datetime.now()
        return await self._executor.submit(
            self._open_shell_sync, term, width, height, timeout=self.config.timeout
        )

    def _open_shell_sync(self, term: str, width: int, height: int) -> paramiko.Channel:
        assert self.client is not None
        return self.client.invoke_shell(term=term, width=width, height=height)

    async def upload_file(self, local_path: str, remote_path: str) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")

        # 🔒 安全验证：本地路径验证（防止路径遍历）
        try:
            from .security import SecurityError, path_validator

            safe_local = path_validator.validate_path(local_path)
        except (ImportError, SecurityError):
            # 如果 security 模块不可用或路径验证失败，使用基础安全检查
            if ".." in local_path or local_path.startswith("~"):
                return {
                    "success": False,
                    "message": "Invalid local path: path traversal detected",
                    "session_id": self.session_id,
                }

        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._upload_file_sync, local_path, remote_path, timeout=60
            )

    def _upload_file_sync(self, local_path: str, remote_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return {
                "success": True,
                "message": f"File uploaded: {local_path} -> {remote_path}",
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Upload failed: {str(e)}",
                "session_id": self.session_id,
            }

    async def download_file(self, remote_path: str, local_path: str) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")

        # 🔒 安全验证：下载目标路径验证（防止写入到禁止目录）
        try:
            from .security import SecurityError, path_validator

            safe_local = path_validator.validate_path(local_path)
        except (ImportError, SecurityError):
            if ".." in local_path or local_path.startswith("~"):
                return {
                    "success": False,
                    "message": "Invalid local path: path traversal detected",
                    "session_id": self.session_id,
                }

        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._download_file_sync, remote_path, local_path, timeout=60
            )

    def _download_file_sync(self, remote_path: str, local_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return {
                "success": True,
                "message": f"File downloaded: {remote_path} -> {local_path}",
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Download failed: {str(e)}",
                "session_id": self.session_id,
            }

    async def list_directory(self, remote_path: str = ".") -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(self._list_directory_sync, remote_path, timeout=30)

    def _list_directory_sync(self, remote_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return {
                "success": True,
                "files": files,
                "path": remote_path,
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"List failed: {str(e)}",
                "session_id": self.session_id,
            }

    async def write_file(self, remote_path: str, content: str, append: bool = False) -> dict:
        """通过 SFTP 写入或追加内容到远程文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._write_file_sync, remote_path, content, append, timeout=60
            )

    def _write_file_sync(self, remote_path: str, content: str, append: bool = False) -> dict:
        assert self.client is not None
        sftp = None
        try:
            sftp = self.client.open_sftp()
            mode = "a" if append else "w"
            with sftp.open(remote_path, mode) as f:
                f.write(content)
            return {
                "success": True,
                "message": f"File {'appended' if append else 'written'}: {remote_path} ({len(content)} bytes)",
                "bytes_transferred": len(content),
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Write failed: {str(e)}",
                "session_id": self.session_id,
            }
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass

    async def stat_file(self, remote_path: str) -> dict:
        """通过 SFTP 获取远程文件元信息"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(self._stat_file_sync, remote_path, timeout=30)

    def _stat_file_sync(self, remote_path: str) -> dict:
        assert self.client is not None
        sftp = None
        try:
            sftp = self.client.open_sftp()
            st = sftp.stat(remote_path)
            import stat as stat_mod

            is_dir = stat_mod.S_ISDIR(st.st_mode)
            is_link = stat_mod.S_ISLNK(st.st_mode)
            return {
                "success": True,
                "path": remote_path,
                "size": st.st_size,
                "mode": oct(st.st_mode),
                "is_dir": is_dir,
                "is_file": stat_mod.S_ISREG(st.st_mode),
                "is_link": is_link,
                "mtime": st.st_mtime,
                "atime": st.st_atime,
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Stat failed: {str(e)}",
                "session_id": self.session_id,
            }
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass

    async def delete_file(self, remote_path: str) -> dict:
        """通过 SFTP 删除远程文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(self._delete_file_sync, remote_path, timeout=30)

    def _delete_file_sync(self, remote_path: str) -> dict:
        assert self.client is not None
        sftp = None
        try:
            sftp = self.client.open_sftp()
            sftp.remove(remote_path)
            return {
                "success": True,
                "message": f"Deleted: {remote_path}",
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Delete failed: {str(e)}",
                "session_id": self.session_id,
            }
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass

    async def make_dir(self, remote_path: str) -> dict:
        """通过 SFTP 创建远程目录"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(self._make_dir_sync, remote_path, timeout=30)

    def _make_dir_sync(self, remote_path: str) -> dict:
        assert self.client is not None
        sftp = None
        try:
            sftp = self.client.open_sftp()
            try:
                sftp.mkdir(remote_path)
            except OSError:
                # 目录已存在时 SFTP 会抛 OSError,检查确认后视为成功(幂等)
                try:
                    st = sftp.stat(remote_path)
                    import stat as _stat

                    if not _stat.S_ISDIR(st.st_mode):
                        return {
                            "success": False,
                            "message": f"Not a directory: {remote_path}",
                            "session_id": self.session_id,
                        }
                except OSError:
                    raise
            return {
                "success": True,
                "message": f"Directory created: {remote_path}",
                "session_id": self.session_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Mkdir failed: {str(e)}",
                "session_id": self.session_id,
            }
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass

    async def disconnect(self) -> None:
        async with self._connect_lock:
            self._shutdown_event.set()
            if self._keepalive_task:
                self._keepalive_task.cancel()
                self._keepalive_task = None
            # Close any lingering background channels
            for stdin, stdout, stderr in self._background_channels:
                try:
                    stdout.channel.close()
                except Exception:
                    pass
            self._background_channels.clear()
            if self.client:
                await self._executor.submit(self.client.close)
                self.client = None
            self._state = SessionState.DISCONNECTED

    def _get_session_info(self) -> SessionInfo:
        return SessionInfo(
            session_id=self.session_id,
            host=self.config.host,
            port=self.config.port,
            username=self.config.username,
            state=self._state,
            connected_at=self._connected_at or datetime.now(),
            last_activity=self._last_activity,
            last_keepalive=self._last_keepalive,
        )


class SessionManager:
    # 🔒 安全限制：最大并发会话数（防止资源耗尽 DoS）
    # 可通过环境变量 SSH_MAX_SESSIONS / SSH_MAX_SESSIONS_PER_HOST 覆盖
    MAX_SESSIONS = 20
    MAX_SESSIONS_PER_HOST = 5  # 每个主机最多 5 个并发会话

    def __init__(self):
        self._sessions: dict[str, SSHSession] = {}
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._timeout_cleanup_task: asyncio.Task | None = None
        self._logger = get_logger("SessionManager")
        # 环境变量覆盖每主机会话上限与全局会话上限（与 sshd MaxSessions 解耦）
        # 注意：这是 MCP 应用层限制，独立于 sshd 的 MaxSessions
        self.MAX_SESSIONS = max(1, int(os.getenv("SSH_MAX_SESSIONS", str(type(self).MAX_SESSIONS))))
        self.MAX_SESSIONS_PER_HOST = max(
            1, int(os.getenv("SSH_MAX_SESSIONS_PER_HOST", str(type(self).MAX_SESSIONS_PER_HOST)))
        )
        self._start_timeout_cleanup()
        self._session_counter = 0  # 用于统计和限制

    def _start_timeout_cleanup(self):
        async def cleanup_loop():
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(60)
                    await self._cleanup_timeout_sessions()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Session cleanup error: {e}")

        try:
            loop = asyncio.get_running_loop()
            self._timeout_cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            self._timeout_cleanup_task = None

    async def _cleanup_timeout_sessions(self):
        async with self._lock:
            now = datetime.now()
            timeout_sessions = []

            for session_id, session in self._sessions.items():
                if session.is_connected:
                    idle_time = now - session._last_activity
                    if idle_time > timedelta(seconds=session.config.session_timeout):
                        timeout_sessions.append(session_id)

            for session_id in timeout_sessions:
                try:
                    session = self._sessions[session_id]
                    await session.disconnect()
                    del self._sessions[session_id]
                    print(f"Cleaned up timeout session: {session_id}")
                except Exception as e:
                    print(f"Error cleaning up session {session_id}: {e}")

    async def create_session(self, config: ConnectionConfig, reuse: bool = True) -> SessionInfo:
        async with self._lock:
            # 🔄 会话复用：优先复用同一主机+端口+用户的活跃会话
            # 注意：必须比较 port，否则同 host 不同端口（如跳板机多端口）会复用错误 session
            if reuse:
                for session in self._sessions.values():
                    if (
                        session.config.host == config.host
                        and session.config.port == config.port
                        and session.config.username == config.username
                        and session.is_connected
                    ):
                        return session._get_session_info()

            # 🔒 安全检查：会话并发数限制
            if len(self._sessions) >= self.MAX_SESSIONS:
                raise ConnectionException(
                    f"达到最大会话数限制 ({self.MAX_SESSIONS})，请先关闭一些会话"
                )

            # 🔒 安全检查：每个主机会话数限制
            host_sessions = sum(1 for s in self._sessions.values() if s.config.host == config.host)
            if host_sessions >= self.MAX_SESSIONS_PER_HOST:
                raise ConnectionException(
                    f"主机 {config.host} 已达到最大会话数限制 ({self.MAX_SESSIONS_PER_HOST})"
                )

            session = SSHSession(config)
            session_info = await session.connect()
            self._sessions[session.session_id] = session
            self._session_counter += 1
            return session_info

    async def get_session(self, session_id: str, auto_reconnect: bool = True) -> SSHSession | None:
        async with self._lock:
            session = self._sessions.get(session_id)

            # 🔄 自动重连机制：如果 session 存在但已断开，尝试重连
            if session and not session.is_connected and auto_reconnect:
                # 非真实 SSHSession 实例（如测试 Mock）不尝试重连，直接清理
                if not isinstance(session, SSHSession):
                    self._logger.warning(
                        f"Session {session_id} 不是真实会话对象，跳过重连并清理"
                    )
                    result = session.disconnect()
                    if result is not None and inspect.isawaitable(result):
                        await result
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                    return None

                # 检查重连次数限制
                if session._reconnect_count >= session._max_reconnects:
                    self._logger.error(
                        f"Session {session_id} 重连次数已达上限 ({session._max_reconnects})，不再重连"
                    )
                    await session.disconnect()
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                    return None

                self._logger.warning(
                    f"Session {session_id} 已断开，尝试自动重连（重连次数：{session._reconnect_count}/{session._max_reconnects}）"
                )
                try:
                    # 保存配置信息用于重连
                    config = session.config
                    session._reconnect_count += 1

                    # 清理旧 session
                    await session.disconnect()
                    if session_id in self._sessions:
                        del self._sessions[session_id]

                    # 创建新 session（使用相同的 session_id）
                    new_session = SSHSession(config)
                    new_session.session_id = session_id  # 复用原来的 session_id
                    new_session._reconnect_count = session._reconnect_count  # 保持重连次数
                    await new_session.connect()
                    self._sessions[session_id] = new_session
                    self._logger.info(f"Session {session_id} 自动重连成功")
                    return new_session
                except Exception as e:
                    self._logger.error(f"Session {session_id} 自动重连失败: {e}")
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                    return None

            # 🧹 清理完全失效的 session
            if session and not session.is_connected:
                self._logger.warning(
                    f"Session {session_id} 已断开，清理（host={session.config.host}）"
                )
                await session.disconnect()
                if session_id in self._sessions:
                    del self._sessions[session_id]
                return None

            return session

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await session.disconnect()

    async def close_all_sessions(self) -> None:
        async with self._lock:
            for session in list(self._sessions.values()):
                await session.disconnect()
            self._sessions.clear()

    def list_sessions(self) -> list[SessionInfo]:
        return [session._get_session_info() for session in self._sessions.values()]

    async def shutdown(self):
        self._shutdown_event.set()
        if self._timeout_cleanup_task:
            self._timeout_cleanup_task.cancel()
        await self.close_all_sessions()

    async def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: int = 30,
        background: bool = False,
        stdin_data: str | None = None,
        get_pty: bool = False,
    ) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.execute_command(
            command, timeout, background, stdin_data=stdin_data, get_pty=get_pty
        )

    async def upload_file(self, session_id: str, local_path: str, remote_path: str) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.upload_file(local_path, remote_path)

    async def download_file(self, session_id: str, remote_path: str, local_path: str) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.download_file(remote_path, local_path)

    async def list_directory(self, session_id: str, remote_path: str = ".") -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.list_directory(remote_path)

    async def write_file(
        self, session_id: str, remote_path: str, content: str, append: bool = False
    ) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.write_file(remote_path, content, append)

    async def stat_file(self, session_id: str, remote_path: str) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.stat_file(remote_path)

    async def delete_file(self, session_id: str, remote_path: str) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.delete_file(remote_path)

    async def make_dir(self, session_id: str, remote_path: str) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.make_dir(remote_path)
