from __future__ import annotations

import asyncio
import threading
import os
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

import paramiko
from paramiko import SSHClient, AutoAddPolicy, SFTPClient, HostKeys, RejectPolicy, WarningPolicy
from pathlib import Path

from .connection_config import ConnectionConfig
from .executor import get_executor


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
    error_message: Optional[str] = None
    last_keepalive: datetime = field(default_factory=datetime.now)


class SSHSession:
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: Optional[SSHClient] = None
        self.session_id = str(uuid.uuid4())
        self._state = SessionState.DISCONNECTED
        self._connected_at: Optional[datetime] = None
        self._last_activity: datetime = datetime.now()
        self._last_keepalive: datetime = datetime.now()
        self._keepalive_task: Optional[asyncio.Task] = None
        self._executor = get_executor()
        self._connect_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == SessionState.CONNECTED and self.client is not None

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
            'hostname': self.config.host,
            'port': self.config.port,
            'username': self.config.username,
            'timeout': self.config.timeout,
            'compress': self.config.compress,
            'look_for_keys': self.config.look_for_keys,
            'allow_agent': self.config.allow_agent,
        }
        
        if self.config.auth_method == "password" and self.config.password:
            connect_kwargs['password'] = self.config.password
        elif self.config.auth_method == "private_key" and self.config.private_key_path:
            connect_kwargs['key_filename'] = str(self.config.private_key_path)
            if self.config.passphrase:
                connect_kwargs['passphrase'] = self.config.passphrase
        
        self.client.connect(**connect_kwargs)
        
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
                    if transport:
                        await self._executor.submit(transport.send_ignore)
                        self._last_keepalive = datetime.now()
                except Exception as e:
                    print(f"Keepalive failed for session {self.session_id}: {e}")
                    break
        
        self._keepalive_task = asyncio.create_task(keepalive_loop())

    async def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        async with self._connect_lock:
            self._state = SessionState.EXECUTING
            self._last_activity = datetime.now()
            try:
                result = await self._executor.submit(
                    self._execute_command_sync, command, timeout, background,
                    timeout=timeout + 5
                )
                return result
            finally:
                self._state = SessionState.CONNECTED

    def _execute_command_sync(self, command: str, timeout: int, background: bool = False) -> dict:
        assert self.client is not None
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        
        if background:
            try:
                pid = stdout.channel.pid
                pid_msg = f"PID: {pid}"
            except AttributeError:
                pid_msg = "background mode"
            
            return {
                "exit_code": 0,
                "stdout": f"Command started in {pid_msg}",
                "stderr": "",
                "session_id": self.session_id
            }
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode('utf-8', errors='replace')
        stderr_data = stderr.read().decode('utf-8', errors='replace')
        
        return {
            "exit_code": exit_code,
            "stdout": stdout_data,
            "stderr": stderr_data,
            "session_id": self.session_id
        }

    async def execute_command_stream(
        self, command: str
    ) -> AsyncIterator[str]:
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

    def _execute_command_stream_sync(self, command: str) -> AsyncIterator[str]:
        assert self.client is not None
        
        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')

    async def _async_stream_wrapper(self, sync_iterator):
        loop = asyncio.get_event_loop()
        while True:
            try:
                item = await loop.run_in_executor(
                    self._executor.executor,
                    lambda: next(sync_iterator, None)
                )
                if item is None:
                    break
                yield item
            except StopIteration:
                break

    async def open_shell(self, term: str = "xterm", width: int = 80, height: int = 24) -> paramiko.Channel:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        self._last_activity = datetime.now()
        return await self._executor.submit(
            self._open_shell_sync, term, width, height,
            timeout=self.config.timeout
        )

    def _open_shell_sync(self, term: str, width: int, height: int) -> paramiko.Channel:
        assert self.client is not None
        return self.client.invoke_shell(term=term, width=width, height=height)

    async def upload_file(self, local_path: str, remote_path: str) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        # 🔒 安全验证：本地路径验证（防止路径遍历）
        try:
            from .security import path_validator, SecurityError
            safe_local = path_validator.validate_path(local_path)
        except (ImportError, SecurityError):
            # 如果 security 模块不可用或路径验证失败，使用基础安全检查
            import re
            if '..' in local_path or local_path.startswith('~'):
                return {"success": False, "message": "Invalid local path: path traversal detected", "session_id": self.session_id}
        
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._upload_file_sync, local_path, remote_path,
                timeout=60
            )

    def _upload_file_sync(self, local_path: str, remote_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}", "session_id": self.session_id}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}", "session_id": self.session_id}

    async def download_file(self, remote_path: str, local_path: str) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        # 🔒 安全验证：下载目标路径验证（防止写入到禁止目录）
        try:
            from .security import path_validator, SecurityError
            safe_local = path_validator.validate_path(local_path)
        except (ImportError, SecurityError):
            import re
            if '..' in local_path or local_path.startswith('~'):
                return {"success": False, "message": "Invalid local path: path traversal detected", "session_id": self.session_id}
        
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._download_file_sync, remote_path, local_path,
                timeout=60
            )

    def _download_file_sync(self, remote_path: str, local_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}", "session_id": self.session_id}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}", "session_id": self.session_id}

    async def list_directory(self, remote_path: str = ".") -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        async with self._connect_lock:
            self._last_activity = datetime.now()
            return await self._executor.submit(
                self._list_directory_sync, remote_path,
                timeout=30
            )

    def _list_directory_sync(self, remote_path: str) -> dict:
        assert self.client is not None
        try:
            sftp = self.client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return {"success": True, "files": files, "path": remote_path, "session_id": self.session_id}
        except Exception as e:
            return {"success": False, "message": f"List failed: {str(e)}", "session_id": self.session_id}

    async def disconnect(self) -> None:
        async with self._connect_lock:
            self._shutdown_event.set()
            if self._keepalive_task:
                self._keepalive_task.cancel()
                self._keepalive_task = None
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
            last_keepalive=self._last_keepalive
        )


class SessionManager:
    # 🔒 安全限制：最大并发会话数（防止资源耗尽 DoS）
    MAX_SESSIONS = 10
    MAX_SESSIONS_PER_HOST = 3  # 每个主机最多 3 个并发会话
    
    def __init__(self):
        self._sessions: dict[str, SSHSession] = {}
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._timeout_cleanup_task: Optional[asyncio.Task] = None
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

    async def create_session(self, config: ConnectionConfig) -> SessionInfo:
        async with self._lock:
            # 🔒 安全检查：会话并发数限制
            if len(self._sessions) >= self.MAX_SESSIONS:
                raise ConnectionException(
                    f"达到最大会话数限制 ({self.MAX_SESSIONS})，请先关闭一些会话"
                )
            
            # 🔒 安全检查：每个主机会话数限制
            host_sessions = sum(
                1 for s in self._sessions.values()
                if s.config.host == config.host
            )
            if host_sessions >= self.MAX_SESSIONS_PER_HOST:
                raise ConnectionException(
                    f"主机 {config.host} 已达到最大会话数限制 ({self.MAX_SESSIONS_PER_HOST})"
                )
            
            session = SSHSession(config)
            session_info = await session.connect()
            self._sessions[session.session_id] = session
            self._session_counter += 1
            return session_info

    async def get_session(self, session_id: str) -> Optional[SSHSession]:
        async with self._lock:
            return self._sessions.get(session_id)

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
        return [
            session._get_session_info()
            for session in self._sessions.values()
        ]

    async def shutdown(self):
        self._shutdown_event.set()
        if self._timeout_cleanup_task:
            self._timeout_cleanup_task.cancel()
        await self.close_all_sessions()

    async def execute_command(self, session_id: str, command: str, timeout: int = 30, background: bool = False) -> dict:
        session = await self.get_session(session_id)
        if not session:
            raise ConnectionError(f"Session {session_id} not found")
        return await session.execute_command(command, timeout, background)

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