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
    
    def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> CommandResult:
        """执行命令并返回结果
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            background: 是否后台执行（不等待命令完成）
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            if background:
                # Fabric doesn't have native background execution, use nohup
                nohup_command = f"nohup {command} > /dev/null 2>&1 &"
                self._connection.run(nohup_command, timeout=timeout, hide=True)
                return CommandResult(
                    stdout="Command started in background",
                    stderr="",
                    return_code=0
                )
            
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
    
    def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> CommandResult:
        """执行命令
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            background: 是否后台执行（不等待命令完成）
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        import sys
        if background:
            # AsyncSSH: run in background
            bg_command = f"nohup {command} > /dev/null 2>&1 &"
            if sys.platform == 'win32':
                import asyncio
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._connection.run(bg_command, timeout=timeout))
            else:
                _run_async(self._connection.run(bg_command, timeout=timeout))
            return CommandResult(
                stdout="Command started in background",
                stderr="",
                return_code=0
            )
        
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


class SystemSSHClient(SSHClientInterface):
    """基于系统 SSH 命令的客户端（最稳定）"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
    
    @property
    def client_type(self) -> ClientType:
        return ClientType.SYSTEM
    
    @property
    def is_connected(self) -> bool:
        return True
    
    def connect(self, timeout: int = 30) -> None:
        """系统 SSH 不需要持久连接"""
        pass
    
    def _build_ssh_command(self, command: str) -> list[str]:
        """构建 SSH 命令"""
        ssh_cmd = ["ssh"]
        
        if self.config.port != 22:
            ssh_cmd.extend(["-p", str(self.config.port)])
        
        if self.config.auth_method == "private_key" and self.config.private_key_path:
            ssh_cmd.extend(["-i", str(self.config.private_key_path)])
        
        ssh_cmd.extend([
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={timeout}",
            f"{self.config.username}@{self.config.host}",
            command
        ])
        
        return ssh_cmd
    
    def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> CommandResult:
        """执行命令（带安全验证）"""
        import subprocess
        from ..security import SecurityError, command_validator
        
        # 🔒 安全验证 - 防止任意命令执行
        try:
            command_validator.validate_command(command)
        except SecurityError as e:
            self._logger.error(f"Command blocked: {e}")
            return CommandResult(
                stdout="",
                stderr=f"安全错误：{str(e)}",
                return_code=1
            )
        
        ssh_cmd = self._build_ssh_command(command)
        
        try:
            if background:
                # 后台执行：不等待命令完成
                import os
                process = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return CommandResult(
                    stdout=f"Command started in background (PID: {process.pid})",
                    stderr="",
                    return_code=0
                )
            
            # 前台执行：等待命令完成
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                stdout="",
                stderr="Command timed out",
                return_code=124
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=1
            )
    
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令"""
        import subprocess
        
        ssh_cmd = self._build_ssh_command(command)
        
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            yield line
        
        process.wait()
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件（使用 scp，带路径验证）"""
        import subprocess
        import shlex
        from ..security import SecurityError, path_validator
        
        # 🔒 验证远程路径
        try:
            safe_remote_path = str(path_validator.validate_path(remote_path))
        except SecurityError as e:
            self._logger.error(f"Path blocked: {e}")
            return {
                'success': False,
                'error': f"安全错误：{str(e)}"
            }
        
        scp_cmd = [
            "scp",
            "-P", str(self.config.port),
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={self.config.timeout}",
        ]
        
        if self.config.auth_method == "private_key" and self.config.private_key_path:
            scp_cmd.extend(["-i", str(self.config.private_key_path)])
        
        scp_cmd.extend([
            shlex.quote(local_path),
            f"{self.config.username}@{self.config.host}:{shlex.quote(safe_remote_path)}"
        ])
        
        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            if result.returncode == 0:
                return {"success": True, "message": f"File uploaded: {local_path} -> {remote_path}"}
            else:
                return {"success": False, "message": f"Upload failed: {result.stderr}"}
        except Exception as e:
            return {"success": False, "message": f"Upload failed: {str(e)}"}
    
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件（使用 scp，带路径验证）"""
        import subprocess
        import shlex
        from ..security import SecurityError, path_validator
        
        # 🔒 验证远程路径
        try:
            safe_remote_path = str(path_validator.validate_path(remote_path))
        except SecurityError as e:
            self._logger.error(f"Path blocked: {e}")
            return {
                'success': False,
                'error': f"安全错误：{str(e)}"
            }
        
        scp_cmd = [
            "scp",
            "-P", str(self.config.port),
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={self.config.timeout}",
        ]
        
        if self.config.auth_method == "private_key" and self.config.private_key_path:
            scp_cmd.extend(["-i", str(self.config.private_key_path)])
        
        scp_cmd.extend([
            f"{self.config.username}@{self.config.host}:{shlex.quote(safe_remote_path)}",
            shlex.quote(local_path)
        ])
        
        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            if result.returncode == 0:
                return {"success": True, "message": f"File downloaded: {remote_path} -> {local_path}"}
            else:
                return {"success": False, "message": f"Download failed: {result.stderr}"}
        except Exception as e:
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录（带路径验证）"""
        from ..security import SecurityError, path_validator
        
        # 🔒 验证路径
        try:
            safe_path = str(path_validator.validate_path(remote_path))
        except SecurityError as e:
            self._logger.error(f"Path blocked: {e}")
            return FileListResult(files=[], path=remote_path, error=f"安全错误：{str(e)}")
        
        result = self.execute_command(f"ls -la {safe_path}")
        if result.return_code == 0:
            files = [line.split()[-1] for line in result.stdout.splitlines() if line.strip() and not line.startswith("total")]
            return FileListResult(files=files, path=safe_path)
        return FileListResult(files=[], path=remote_path)
    
    def close(self) -> None:
        """关闭连接（无操作）"""
        pass


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
    
    def execute_command(self, command: str, timeout: int = 30, background: bool = False) -> CommandResult:
        """执行命令"""
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        try:
            stdin, stdout, stderr = self._session.command(command)
            
            if background:
                # 后台执行：不等待命令完成，立即返回
                return CommandResult(
                    stdout="Command started in background",
                    stderr="",
                    return_code=0
                )
            
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
