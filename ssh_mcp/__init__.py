"""SSH MCP Server - Model Context Protocol Server for SSH functionality."""

__version__ = "0.1.0"

__all__ = [
    "SSHMCPServer",
    "KeyManager",
    "SSHKeyPair",
    "ConnectionConfig",
    "ClientType",
    "SessionManager",
    "SSHSession",
    "SessionInfo",
    "ConfigManager",
    "SSHConfig",
    "SSHService",
    "get_ssh_service",
    "SSHException",
    "ConnectionException",
    "AuthenticationException",
    "CommandExecutionException",
    "FileTransferException",
    "SessionException",
    "TimeoutException",
    "ConfigurationException",
    "get_logger",
    "SSHLogger",
]

from .server import SSHMCPServer
from .key_manager import KeyManager, SSHKeyPair
from .connection_config import ConnectionConfig, ClientType
from .session_manager import SessionManager, SSHSession, SessionInfo
from .config_manager import ConfigManager, SSHConfig
from .service import SSHService, get_ssh_service
from .exceptions import (
    SSHException,
    ConnectionException,
    AuthenticationException,
    CommandExecutionException,
    FileTransferException,
    SessionException,
    TimeoutException,
    ConfigurationException,
)
from .logging_config import get_logger, SSHLogger
