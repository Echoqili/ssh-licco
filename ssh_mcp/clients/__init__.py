"""
SSH 客户端模块

支持多种 SSH 客户端实现：
- Paramiko: 纯 Python 实现，功能完善
- Fabric: 基于 Paramiko的高级 API
- AsyncSSH: 异步高性能
- SSH2: C 扩展，极致性能
- System: subprocess 调用系统 SSH，最稳定
"""

from .interface import (
    SSHClientInterface,
    ClientType,
    CommandResult,
    FileListResult,
)
from .factory import (
    SSHClientFactory,
    ClientConfig,
    get_client_config,
)

__all__ = [
    "SSHClientInterface",
    "ClientType",
    "CommandResult",
    "FileListResult",
    "SSHClientFactory",
    "ClientConfig",
    "get_client_config",
]
