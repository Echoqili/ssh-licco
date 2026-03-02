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


class PoolExhaustedException(SSHException):
    """连接池耗尽异常"""
    
    def __init__(self, message: str = "Connection pool is exhausted",
                 original_error: Optional[Exception] = None):
        super().__init__(message, original_error)


class RetryExhaustedException(SSHException):
    """重试次数耗尽异常"""
    
    def __init__(self, message: str, attempts: int = 0,
                 original_error: Optional[Exception] = None):
        full_message = f"Retry exhausted after {attempts} attempts: {message}"
        super().__init__(full_message, original_error)
        self.attempts = attempts
