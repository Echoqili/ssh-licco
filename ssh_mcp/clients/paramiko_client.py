from __future__ import annotations

import time
from typing import AsyncIterator
from pathlib import Path

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..connection_config import ConnectionConfig
from ..exceptions import ConnectionException, CommandExecutionException, FileTransferException
from ..logging_config import get_logger
from .interface import (
    SSHClientInterface, 
    ClientType, 
    CommandResult, 
    FileListResult,
    ConnectionResult,
    FileTransferResult
)


class ParamikoClient(SSHClientInterface):
    """基于 Paramiko 的 SSH 客户端实现
    
    特性：
    - 纯 Python 实现，无外部依赖
    - 支持密码和密钥认证
    - 支持 SFTP 文件传输
    - 内置 keepalive 保活机制
    - 完整的错误处理
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
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()
    
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
                'look_for_keys': self.config.look_for_keys,
                'allow_agent': self.config.allow_agent,
            }
            
            if self.config.auth_method == "password" and self.config.password:
                connect_kwargs['password'] = self.config.password
            elif self.config.auth_method == "private_key" and self.config.private_key_path:
                connect_kwargs['key_filename'] = str(self.config.private_key_path)
                if self.config.passphrase:
                    connect_kwargs['passphrase'] = self.config.passphrase
            else:
                # Default to password authentication if password is provided
                if self.config.password:
                    connect_kwargs['password'] = self.config.password
            
            self.client.connect(**connect_kwargs)
            
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
            
        except paramiko.AuthenticationException as e:
            self._logger.error(f"Authentication failed: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"Authentication failed: {str(e)}"
            )
        except paramiko.SSHException as e:
            self._logger.error(f"SSH error: {str(e)}")
            return ConnectionResult(
                success=False,
                message=f"SSH error: {str(e)}"
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
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令并返回结果
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            
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
        
        try:
            stdin, stdout, stderr = self.client.exec_command(
                command, 
                timeout=timeout
            )
            
            return_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            
            return CommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
                return_code=return_code
            )
            
        except Exception as e:
            self._logger.error(f"Command execution failed: {str(e)}")
            raise CommandExecutionException(
                f"Failed to execute command: {str(e)}",
                command=command,
                original_error=e
            )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
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
        
        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')
    
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
        
        transport = self.client.get_transport()
        
        return {
            "connected": True,
            "cipher": transport.get_remote_cipher() if transport else None,
            "key_type": transport.get_remote_key_type() if transport else None,
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
