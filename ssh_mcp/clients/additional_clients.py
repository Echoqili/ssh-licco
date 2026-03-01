from __future__ import annotations

import asyncio
import sys
from typing import AsyncIterator
from pathlib import Path

from ..connection_config import ConnectionConfig
from .interface import SSHClientInterface, ClientType, CommandResult, FileListResult


def _run_async(coro):
    """在 Windows 上使用 ProactorEventLoop 运行异步代码"""
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            pass
    else:
        return asyncio.run(coro)


class FabricClient(SSHClientInterface):
    """基于 Fabric 的 SSH 客户端实现"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connection = None
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.FABRIC
    
    @property
    def is_connected(self) -> bool:
        return self._connection is not None
    
    def connect(self, timeout: int = 30) -> None:
        """建立 SSH 连接"""
        try:
            from fabric import Connection
            
            self._connection = Connection(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                connect_timeout=timeout,
            )
            
            if self.config.auth_method == "password" and self.config.password:
                self._connection.connect_kwargs["password"] = self.config.password
            elif self.config.auth_method == "private_key" and self.config.private_key_path:
                self._connection.connect_kwargs["key_filename"] = str(self.config.private_key_path)
                if self.config.passphrase:
                    self._connection.connect_kwargs["passphrase"] = self.config.passphrase
            
            self._connection.open()
        except ImportError:
            raise ImportError("Fabric is not installed. Install with: pip install fabric")
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令并返回结果"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            result = self._connection.run(command, timeout=timeout, hide=True)
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.exit_code
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=1
            )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        result = self._connection.run(command, hide=False, pty=True)
        for line in result.stdout.splitlines():
            yield line + "\n"
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            self._connection.put(local_path, remote_path)
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            self._connection.get(remote_path, local_path)
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录内容"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            result = self._connection.run(f"ls -la {remote_path}", hide=True)
            files = [line.split()[-1] for line in result.stdout.splitlines() if line.strip()]
            return FileListResult(files=files, path=remote_path)
        except Exception:
            return FileListResult(files=[], path=remote_path)
    
    def close(self) -> None:
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None


class AsyncSSHClient(SSHClientInterface):
    """基于 AsyncSSH 的异步 SSH 客户端"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connection = None
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.ASYNCSSH
    
    @property
    def is_connected(self) -> bool:
        return self._connection is not None
    
    def connect(self, timeout: int = 30) -> None:
        """同步连接（异步版本）"""
        try:
            import asyncssh
            import sys
            
            connect_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'username': self.config.username,
                'known_hosts': None,
                'server_host_key_algs': ['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-ed25519'],
                'encryption_algs': (
                    'aes256-ctr,aes192-ctr,aes128-ctr,'
                    'aes256-gcm@openssh.com,aes128-gcm@openssh.com,'
                    'aes256-cbc,aes192-cbc,aes128-cbc,3des-cbc'
                ),
            }
            
            if self.config.auth_method == "password" and self.config.password:
                connect_kwargs['password'] = self.config.password
            elif self.config.auth_method == "private_key" and self.config.private_key_path:
                connect_kwargs['client_keys'] = [str(self.config.private_key_path)]
                if self.config.passphrase:
                    connect_kwargs['passphrase'] = self.config.passphrase
            else:
                if self.config.password:
                    connect_kwargs['password'] = self.config.password
            
            if sys.platform == 'win32':
                import asyncio
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
                try:
                    self._connection = loop.run_until_complete(asyncssh.connect(**connect_kwargs))
                finally:
                    pass
            else:
                async def do_connect():
                    return await asyncssh.connect(**connect_kwargs)
                self._connection = _run_async(do_connect())
        except ImportError:
            raise ImportError("AsyncSSH is not installed. Install with: pip install asyncssh")
    
    async def connect_async(self, timeout: int = 30) -> None:
        """异步连接"""
        try:
            import asyncssh
            
            connect_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'username': self.config.username,
                'client_keys': None,
                'known_hosts': None,
            }
            
            if self.config.auth_method == "password" and self.config.password:
                connect_kwargs['password'] = self.config.password
            elif self.config.auth_method == "private_key" and self.config.private_key_path:
                connect_kwargs['client_keys'] = [str(self.config.private_key_path)]
                if self.config.passphrase:
                    connect_kwargs['passphrase'] = self.config.passphrase
            
            self._connection = await asyncssh.connect(**connect_kwargs)
        except ImportError:
            raise ImportError("AsyncSSH is not installed. Install with: pip install asyncssh")
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        import sys
        if sys.platform == 'win32':
            import asyncio
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._connection.run(command, timeout=timeout))
        else:
            result = _run_async(self._connection.run(command, timeout=timeout))
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.exit_code
        )
    
    async def execute_command_async(self, command: str, timeout: int = 30) -> CommandResult:
        """异步执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        result = await self._connection.run(command, timeout=timeout)
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.exit_code
        )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        async def stream():
            async with self._connection.create_process(command) as process:
                async for line in process.stdout:
                    yield line
        
        return stream()
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            _run_async(self._connection.scp(local_path, remote_path))
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    async def upload_file_async(self, local_path: str, remote_path: str) -> dict:
        """异步上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            await self._connection.scp(local_path, remote_path)
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            _run_async(self._connection.scp(remote_path, local_path))
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    async def download_file_async(self, remote_path: str, local_path: str) -> dict:
        """异步下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            await self._connection.scp(remote_path, local_path)
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            result = _run_async(self._connection.run(f"ls -la {remote_path}"))
            files = [line.split()[-1] for line in result.stdout.splitlines() if line.strip()]
            return FileListResult(files=files, path=remote_path)
        except Exception:
            return FileListResult(files=[], path=remote_path)
    
    def close(self) -> None:
        """关闭连接"""
        if self._connection:
            _run_async(self._connection.close())
            self._connection = None
    
    async def close_async(self) -> None:
        """异步关闭连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    def disconnect(self) -> None:
        """断开 SSH 连接"""
        self.close()

    def get_transport_info(self) -> dict:
        """获取传输层信息"""
        if not self.is_connected:
            return {"connected": False}
        
        return {
            "connected": True,
            "host": self.config.host,
            "port": self.config.port,
            "client_type": "asyncssh",
            "remote_version": "unknown",
            "cipher": "unknown",
            "kex": "unknown",
        }


class SSH2Client(SSHClientInterface):
    """基于 SSH2 (libssh2) 的客户端（极致性能）"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._session = None
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.SSH2
    
    @property
    def is_connected(self) -> bool:
        return self._session is not None
    
    def connect(self, timeout: int = 30) -> None:
        """建立 SSH 连接"""
        try:
            import ssh2
            
            self._session = ssh2.Session()
            self._session.connect(
                self.config.host,
                port=self.config.port,
                timeout=timeout
            )
            
            if self.config.auth_method == "password" and self.config.password:
                self._session.userauth_password(self.config.username, self.config.password)
            elif self.config.auth_method == "private_key" and self.config.private_key_path:
                self._session.userauth_publickey_fromfile(
                    self.config.username,
                    str(self.config.private_key_path),
                    passphrase=self.config.passphrase
                )
        except ImportError:
            raise ImportError("SSH2 is not installed. Install with: pip install ssh2-python")
    
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            stdin, stdout, stderr = self._session.command(command)
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            return_code = stdout.channel.get_exit_status()
            
            return CommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
                return_code=return_code
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=1
            )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        stdin, stdout, stderr = self._session.command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self._session.sftp()
            sftp.upload(local_path, remote_path)
            return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self._session.sftp()
            sftp.download(remote_path, local_path)
            return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            sftp = self._session.sftp()
            files = sftp.listdir(remote_path)
            return FileListResult(files=files, path=remote_path)
        except Exception:
            return FileListResult(files=[], path=remote_path)
    
    def close(self) -> None:
        """关闭连接"""
        if self._session:
            self._session.close()
            self._session = None
