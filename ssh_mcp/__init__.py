"""SSH MCP Server - Model Context Protocol Server for SSH functionality."""

__version__ = "0.1.0"

__all__ = [
    "SSHMCPServer",
    "KeyManager",
    "SSHKeyPair",
    "ConnectionConfig",
    "SessionManager",
    "SSHSession",
    "SessionInfo",
    "ConfigManager",
    "SSHConfig",
]

from .server import SSHMCPServer
from .key_manager import KeyManager, SSHKeyPair
from .connection_config import ConnectionConfig
from .session_manager import SessionManager, SSHSession, SessionInfo
from .config_manager import ConfigManager, SSHConfig
