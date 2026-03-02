"""SSH MCP Server - Model Context Protocol Server for SSH functionality."""

__version__ = "0.2.1"

__all__ = [
    "SSHMCPServer",
    "KeyManager",
    "SSHKeyPair",
    "ConnectionConfig",
    "ClientType",
    "RetryConfig",
    "SessionManager",
    "SSHSession",
    "SessionInfo",
    "ConfigManager",
    "SSHConfig",
    "SSHService",
    "get_ssh_service",
    "ConnectionPool",
    "PoolConfig",
    "PooledSSHClient",
    "BatchExecutor",
    "AsyncBatchExecutor",
    "BatchExecutionResult",
    "HostResult",
    "AuditLogger",
    "AuditEventType",
    "get_audit_logger",
    "SSHException",
    "ConnectionException",
    "AuthenticationException",
    "CommandExecutionException",
    "FileTransferException",
    "SessionException",
    "TimeoutException",
    "ConfigurationException",
    "PoolExhaustedException",
    "RetryExhaustedException",
    "get_logger",
    "SSHLogger",
]

from .server import SSHMCPServer
from .key_manager import KeyManager, SSHKeyPair
from .connection_config import ConnectionConfig, ClientType, RetryConfig
from .session_manager import SessionManager, SSHSession, SessionInfo
from .config_manager import ConfigManager, SSHConfig
from .service import SSHService, get_ssh_service
from .connection_pool import ConnectionPool, PoolConfig, PooledSSHClient
from .batch_executor import BatchExecutor, AsyncBatchExecutor, BatchExecutionResult, HostResult
from .audit_logger import AuditLogger, AuditEventType, get_audit_logger
from .exceptions import (
    SSHException,
    ConnectionException,
    AuthenticationException,
    CommandExecutionException,
    FileTransferException,
    SessionException,
    TimeoutException,
    ConfigurationException,
    PoolExhaustedException,
    RetryExhaustedException,
)
from .logging_config import get_logger, SSHLogger
