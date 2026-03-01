from __future__ import annotations

from typing import Optional
from datetime import datetime


class SSHException(Exception):
    """SSH 基础异常类"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error
        self.timestamp = datetime.now()


class ConnectionException(SSHException):
    """连接相关异常"""
    pass


class AuthenticationException(SSHException):
    """认证相关异常"""
    pass


class CommandExecutionException(SSHException):
    """命令执行异常"""
    
    def __init__(self, message: str, command: str = "", return_code: int = -1, 
                 original_error: Optional[Exception] = None):
        super().__init__(message, original_error)
        self.command = command
        self.return_code = return_code


class FileTransferException(SSHException):
    """文件传输异常"""
    pass


class SessionException(SSHException):
    """会话管理异常"""
    pass


class TimeoutException(SSHException):
    """超时异常"""
    pass


class ConfigurationException(SSHException):
    """配置相关异常"""
    pass


class ClientNotAvailableException(SSHException):
    """客户端不可用异常"""
    
    def __init__(self, client_type: str, message: str = "", 
                 original_error: Optional[Exception] = None):
        full_message = f"Client '{client_type}' is not available. {message}"
        super().__init__(full_message, original_error)
        self.client_type = client_type
