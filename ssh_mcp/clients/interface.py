from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum


class ClientType(Enum):
    PARAMIKO = "paramiko"
    FABRIC = "fabric"
    ASYNCSSH = "asyncssh"
    SSH2 = "ssh2"
    SYSTEM = "system"


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    return_code: int


@dataclass
class FileListResult:
    files: list[str]
    path: str


class SSHClientInterface(ABC):
    """SSH 客户端抽象接口"""
    
    @property
    @abstractmethod
    def client_type(self) -> ClientType:
        """返回客户端类型"""
        pass
    
    @abstractmethod
    def connect(self, timeout: int = 30) -> None:
        """建立 SSH 连接"""
        pass
    
    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> CommandResult:
        """执行命令并返回结果"""
        pass
    
    @abstractmethod
    def execute_command_stream(self, command: str) -> AsyncIterator[str]:
        """流式执行命令（用于大输出）"""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """上传文件"""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> dict:
        """下载文件"""
        pass
    
    @abstractmethod
    def list_directory(self, remote_path: str = ".") -> FileListResult:
        """列出目录内容"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        pass
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
