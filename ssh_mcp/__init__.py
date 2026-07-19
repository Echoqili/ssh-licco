# SSH-LICCO 版本信息
# 所有代码中的版本信息都从这里读取
# 版本号：2.5.1

__version__ = "2.5.1"
__author__ = "Li Qi"
__email__ = "1985694657@qq.com"
__license__ = "MIT"
__description__ = "SSH Model Context Protocol Server - Enable SSH functionality for AI models"
__url__ = "https://github.com/Echoqili/ssh-licco"

from ssh_mcp.connection_config import ConnectionConfig
from ssh_mcp.exceptions import (
    AuthenticationException,
    ClientNotAvailableException,
    CommandExecutionException,
    ConfigurationException,
    ConnectionException,
    FileTransferException,
    PoolExhaustedException,
    RetryExhaustedException,
    SessionException,
    SSHException,
    TimeoutException,
)
from ssh_mcp.service import get_ssh_service

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "__url__",
    "ConnectionConfig",
    "SSHException",
    "ConnectionException",
    "AuthenticationException",
    "CommandExecutionException",
    "FileTransferException",
    "SessionException",
    "TimeoutException",
    "ConfigurationException",
    "ClientNotAvailableException",
    "PoolExhaustedException",
    "RetryExhaustedException",
    "get_ssh_service",
]
