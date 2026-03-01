from __future__ import annotations

import asyncio
from typing import AsyncIterator
from pathlib import Path

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..connection_config import ConnectionConfig
from .interface import SSHClientInterface, ClientType, CommandResult, FileListResult


class ParamikoClient(SSHClientInterface):
    """基于 Paramiko 的 SSH 客户端实现"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: SSHClient | None = None
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.PARAMIKO
    
    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.get_transport() is not None
    
    def connect(self, timeout: int = 30) -> None:
        """建立 SSH 连接"""
        if self.is_connected:
            return
        
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
        
        self.client.connect(**connect_kwargs)
        
        # 启用 keepalive
        transport = self.client.get_transport()
        if transport:
            transport.set_keepalive(self.config.keepalive_interval)
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令并返回结果"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        
        return_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode('utf-8', errors='replace')
        stderr_data = stderr.read().decode('utf-8', errors='replace')
        
        return CommandResult(
            stdout=stdout_data,
            stderr=stderr_data,
            return_code=return_code
        )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录内容"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return FileListResult(files=files, path=remote_path)
        except Exception as e:
            return FileListResult(files=[], path=remote_path)
    
    def close(self) -> None:
        """关闭连接"""
        if self.client:
            self.client.close()
            self.client = None


class AsyncParamikoClient(SSHClientInterface):
    """异步 Paramiko 客户端"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: SSHClient | None = None
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.PARAMIKO
    
    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.get_transport() is not None
    
    def connect(self, timeout: int = 30) -> None:
        """同步连接（异步版本）"""
        if self.is_connected:
            return
        
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
        
        self.client.connect(**connect_kwargs)
        
        transport = self.client.get_transport()
        if transport:
            transport.set_keepalive(self.config.keepalive_interval)
    
    async def connect_async(self, timeout: int = 30) -> None:
        """异步连接"""
        await asyncio.get_event_loop().run_in_executor(None, self.connect, timeout)
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        
        return_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode('utf-8', errors='replace')
        stderr_data = stderr.read().decode('utf-8', errors='replace')
        
        return CommandResult(
            stdout=stdout_data,
            stderr=stderr_data,
            return_code=return_code
        )
    
    async def execute_command_async(self, command: str, timeout: int = 30) -> CommandResult:
        """异步执行命令"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.execute_command, command, timeout
        )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    async def upload_file_async(self, local_path: str, remote_path: str) -> dict:
        """异步上传文件"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.upload_file, local_path, remote_path
        )
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    async def download_file_async(self, remote_path: str, local_path: str) -> dict:
        """异步下载文件"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.download_file, remote_path, local_path
        )
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self.client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return FileListResult(files=files, path=remote_path)
        except Exception as e:
            return FileListResult(files=[], path=remote_path)
    
    async def list_directory_async(self, remote_path: str = ".") -> FileListResult:
        """异步列出目录"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.list_directory, remote_path
        )
    
    def close(self) -> None:
        """关闭连接"""
        if self.client:
            self.client.close()
            self.client = None
    
    async def close_async(self) -> None:
        """异步关闭连接"""
        await asyncio.get_event_loop().run_in_executor(None, self.close)
