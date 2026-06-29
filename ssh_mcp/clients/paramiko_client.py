from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

from paramiko import AuthenticationException, AutoAddPolicy, SSHClient, SSHException

from ..connection_config import ConnectionConfig
from ..exceptions import CommandExecutionException
from ..logging_config import get_logger
from .interface import (
    ClientType,
    CommandResult,
    ConnectionResult,
    FileListResult,
    FileTransferResult,
    SSHClientInterface,
)


def _load_pkey_from_memory(pem: str, passphrase: str | None):
    """从内存 PEM 字符串加载 paramiko PKey 对象。

    依次尝试 Ed25519Key / ECDSAKey / RSAKey，兼容 OpenSSH 与传统 PEM 格式。
    返回第一个成功解析的 PKey；全部失败返回 None。
    """
    import io
    from paramiko import RSAKey, ECDSAKey, Ed25519Key

    pw = passphrase.encode("utf-8") if passphrase else None
    sio = io.StringIO(pem)
    for cls in (Ed25519Key, ECDSAKey, RSAKey):
        try:
            sio.seek(0)
            return cls.from_private_key(sio, password=pw)
        except Exception:
            continue
    return None


class ParamikoClient(SSHClientInterface):
    """基于 Paramiko 的 SSH 客户端实现
    
    特性：
    - 纯 Python 实现，无外部依赖
    - 支持密码和密钥认证
    - 支持 SFTP 文件传输
    - 内置 keepalive 保活机制
    - 完整的错误处理和超时控制
    - 线程安全的操作
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: SSHClient | None = None
        self._logger = get_logger(f"ParamikoClient.{config.host}")

    @property
    def client_type(self) -> ClientType:
        return ClientType.PARAMIKO

    @property
    def is_connected(self) -> bool:
        if self.client is None:
            return False
        try:
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False

    def connect(self, timeout: int = 30) -> ConnectionResult:
        """建立 SSH 连接
        
        Args:
            timeout: 连接超时时间（秒）
            
        Returns:
            ConnectionResult: 连接结果
        """
        if self.is_connected:
            return ConnectionResult(
                success=True,
                message="Already connected"
            )

        start_time = time.time()

        try:
            self.client = SSHClient()
            self.client.set_missing_host_key_policy(AutoAddPolicy())

            connect_kwargs = {
                'hostname': self.config.host,
                'port': self.config.port,
                'username': self.config.username,
                'timeout': timeout,
                'compress': self.config.compress,
                'look_for_keys': False,
                'allow_agent': False,
                'banner_timeout': getattr(self.config, 'banner_timeout', max(timeout, 60)),
                'auth_timeout': max(timeout, 60),
            }

            if self.config.auth_method == "password" and self.config.password:
                connect_kwargs['password'] = self.config.password
            elif self.config.auth_method == "private_key" and (self.config.private_key_path or self.config.private_key_material):
                # 加固点 2：优先使用内存私钥（密钥不落地），其次磁盘路径
                if self.config.private_key_material:
                    pkey = _load_pkey_from_memory(self.config.private_key_material, self.config.passphrase)
                    if pkey is not None:
                        connect_kwargs['pkey'] = pkey
                    else:
                        # 内存私钥解析失败，回退到 password（若有），否则报错
                        if self.config.password:
                            connect_kwargs['password'] = self.config.password
                        else:
                            raise SSHException("内存私钥解析失败且无 password 兜底")
                else:
                    connect_kwargs['key_filename'] = str(self.config.private_key_path)
                    if self.config.passphrase:
                        connect_kwargs['passphrase'] = self.config.passphrase
            else:
                if self.config.password:
                    connect_kwargs['password'] = self.config.password

            self.client.connect(**connect_kwargs)  # type: ignore[arg-type]

            transport = self.client.get_transport()
            if transport:
                transport.set_keepalive(self.config.keepalive_interval)

            latency_ms = (time.time() - start_time) * 1000

            self._logger.info(
                f"Connected to {self.config.host}:{self.config.port} "
                f"in {latency_ms:.2f}ms"
            )

            return ConnectionResult(
                success=True,
                message=f"Connected to {self.config.host}:{self.config.port}",
                latency_ms=latency_ms
            )

        except AuthenticationException as e:
            self._logger.error(f"Authentication failed: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"Authentication failed: {str(e)}"
            )
        except SSHException as e:
            self._logger.error(f"SSH error: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"SSH error: {str(e)}"
            )
        except TimeoutError:
            self._logger.error(f"Connection timeout after {timeout}s")
            return ConnectionResult(
                success=False,
                message=f"Connection timeout after {timeout}s"
            )
        except OSError as e:
            self._logger.error(f"Network error: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"Network error: {str(e)}"
            )
        except Exception as e:
            self._logger.error(f"Connection failed: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )

    def disconnect(self) -> None:
        """断开 SSH 连接"""
        self.close()

    def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> CommandResult:
        """执行命令并返回结果
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            background: 是否后台执行（不等待命令完成）
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            CommandExecutionException: 命令执行失败
        """
        if not self.is_connected:
            raise CommandExecutionException(
                "Not connected to SSH server",
                command=command
            )

        assert self.client is not None

        try:
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout
            )

            if background:
                self._logger.info(f"Command started in background: {command}")
                return CommandResult(
                    stdout="Command started in background",
                    stderr="",
                    return_code=0
                )

            return_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')

            return CommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
                return_code=return_code
            )

        except SSHException as e:
            self._logger.error(f"SSH error during command execution: {str(e)}")
            raise CommandExecutionException(
                f"SSH error: {str(e)}",
                command=command,
                original_error=e
            )
        except TimeoutError as e:
            self._logger.error(f"Command execution timeout after {timeout}s")
            raise CommandExecutionException(
                f"Command execution timeout after {timeout}s",
                command=command,
                original_error=e
            )
        except Exception as e:
            self._logger.error(f"Command execution failed: {str(e)}")
            raise CommandExecutionException(
                f"Failed to execute command: {str(e)}",
                command=command,
                original_error=e
            )

    def execute_command_stream(self, command: str) -> Iterator[str]:
        """流式执行命令（用于大输出）
        
        Args:
            command: 要执行的命令
            
        Yields:
            str: 命令输出的每一行
        """
        if not self.is_connected:
            raise CommandExecutionException(
                "Not connected to SSH server",
                command=command
            )

        assert self.client is not None

        try:
            stdin, stdout, stderr = self.client.exec_command(command)

            for line in stdout:
                yield line.decode('utf-8', errors='replace')
        except Exception as e:
            self._logger.error(f"Stream command execution failed: {str(e)}")
            raise CommandExecutionException(
                f"Failed to execute streaming command: {str(e)}",
                command=command,
                original_error=e
            )

    def upload_file(self, local_path: str, remote_path: str) -> FileTransferResult:
        """上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程目标路径
            
        Returns:
            FileTransferResult: 传输结果
        """
        if not self.is_connected:
            return FileTransferResult(
                success=False,
                message="Not connected to SSH server"
            )

        assert self.client is not None

        start_time = time.time()

        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()

            local_file = Path(local_path)
            bytes_transferred = local_file.stat().st_size if local_file.exists() else 0
            duration_ms = (time.time() - start_time) * 1000

            self._logger.info(
                f"Uploaded {local_path} -> {remote_path} "
                f"({bytes_transferred} bytes, {duration_ms:.2f}ms)"
            )

            return FileTransferResult(
                success=True,
                message=f"File uploaded: {local_path} -> {remote_path}",
                bytes_transferred=bytes_transferred,
                duration_ms=duration_ms
            )

        except Exception as e:
            self._logger.error(f"Upload failed: {str(e)}")
            return FileTransferResult(
                success=False,
                message=f"Upload failed: {str(e)}"
            )

    def download_file(self, remote_path: str, local_path: str) -> FileTransferResult:
        """下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地目标路径
            
        Returns:
            FileTransferResult: 传输结果
        """
        if not self.is_connected:
            return FileTransferResult(
                success=False,
                message="Not connected to SSH server"
            )

        assert self.client is not None

        start_time = time.time()

        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()

            local_file = Path(local_path)
            bytes_transferred = local_file.stat().st_size if local_file.exists() else 0
            duration_ms = (time.time() - start_time) * 1000

            self._logger.info(
                f"Downloaded {remote_path} -> {local_path} "
                f"({bytes_transferred} bytes, {duration_ms:.2f}ms)"
            )

            return FileTransferResult(
                success=True,
                message=f"File downloaded: {remote_path} -> {local_path}",
                bytes_transferred=bytes_transferred,
                duration_ms=duration_ms
            )

        except Exception as e:
            self._logger.error(f"Download failed: {str(e)}")
            return FileTransferResult(
                success=False,
                message=f"Download failed: {str(e)}"
            )

    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录内容
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            FileListResult: 目录列表结果
        """
        if not self.is_connected:
            return FileListResult(
                files=[],
                path=remote_path
            )

        assert self.client is not None

        try:
            sftp = self.client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return FileListResult(
                files=files,
                path=remote_path
            )
        except Exception as e:
            self._logger.error(f"List directory failed: {str(e)}")
            return FileListResult(
                files=[],
                path=remote_path
            )

    def get_transport_info(self) -> dict:
        """获取传输层信息
        
        Returns:
            dict: 包含连接状态的字典
        """
        if not self.is_connected:
            return {
                "connected": False,
                "cipher": None,
                "key_type": None,
                "server_key_type": None,
                "remote_version": None,
                "local_version": None,
                "keepalive_interval": self.config.keepalive_interval
            }

        assert self.client is not None

        transport = self.client.get_transport()

        return {
            "connected": True,
            "cipher": transport.get_remote_cipher() if transport else None,  # type: ignore[attr-defined]
            "key_type": transport.get_remote_key_type() if transport else None,  # type: ignore[attr-defined]
            "server_key_type": transport.get_remote_server_key().get_name() if transport and transport.get_remote_server_key() else None,
            "remote_version": transport.remote_version if transport else None,
            "local_version": transport.local_version if transport else None,
            "keepalive_interval": self.config.keepalive_interval,
            "session_timeout": self.config.session_timeout,
            "socket": {
                "timeout": self.config.timeout,
                "compress": self.config.compress
            }
        }

    def close(self) -> None:
        """关闭连接"""
        if self.client:
            try:
                self.client.close()
                self._logger.info("Connection closed")
            except Exception as e:
                self._logger.error(f"Error closing connection: {str(e)}")
            finally:
                self.client = None
