from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum


class ClientType(Enum):
    """支持的 SSH 客户端类型"""
    PARAMIKO = "paramiko"
    FABRIC = "fabric"
    ASYNCSSH = "asyncssh"
    SSH2 = "ssh2"
    SYSTEM = "system"


@dataclass
class CommandResult:
    """命令执行结果"""
    stdout: str
    stderr: str
    return_code: int


@dataclass
class FileListResult:
    """目录列表结果"""
    files: list[str]
    path: str


@dataclass
class ConnectionResult:
    """连接结果"""
    success: bool
    session_id: Optional[str] = None
    message: str = ""
    latency_ms: float = 0.0


@dataclass
class FileTransferResult:
    """文件传输结果"""
    success: bool
    message: str = ""
    bytes_transferred: int = 0
    duration_ms: float = 0.0


class SSHClientInterface(ABC):
    """SSH 客户端抽象接口
    
    所有 SSH 客户端实现必须实现此接口。
    采用依赖倒置原则，便于扩展和测试。
    """
    
    @property
    @abstractmethod
    def client_type(self) -> ClientType:
        """返回客户端类型"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        pass
    
    @abstractmethod
    def connect(self, timeout: int = 30) -> ConnectionResult:
        """建立 SSH 连接
        
        Args:
            timeout: 连接超时时间（秒）
            
        Returns:
            ConnectionResult: 连接结果
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开 SSH 连接"""
        pass
    
    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令并返回结果
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            
        Returns:
            CommandResult: 命令执行结果
        """
        pass
    
    @abstractmethod
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令（用于大输出）
        
        Args:
            command: 要执行的命令
            
        Yields:
            str: 命令输出的每一行
        """
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> FileTransferResult:
        """上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程目标路径
            
        Returns:
            FileTransferResult: 传输结果
        """
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> FileTransferResult:
        """下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地目标路径
            
        Returns:
            FileTransferResult: 传输结果
        """
        pass
    
    @abstractmethod
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录内容
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            FileListResult: 目录列表结果
        """
        pass
    
    @abstractmethod
    def get_transport_info(self) -> dict:
        """获取传输层信息
        
        Returns:
            dict: 包含连接状态的字典
        """
        pass
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        try:
            self.close()
        except Exception:
            pass
