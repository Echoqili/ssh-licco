"""SSH MCP Server - Model Context Protocol Server for SSH functionality."""

__version__ = "0.1.0"

from .server import SSHMCPServer
from .key_manager import KeyManager, SSHKeyPair
from .connection_config import ConnectionConfig, ConnectionProfile
from .session_manager import SessionManager, SSHSession, SessionInfo
from .config_manager import ConfigManager, SSHConfig

__all__ = [
    "SSHMCPServer",
    "KeyManager",
    "SSHKeyPair",
    "ConnectionConfig",
    "ConnectionProfile",
    "SessionManager",
    "SSHSession",
    "SessionInfo",
    "ConfigManager",
    "SSHConfig",
]
