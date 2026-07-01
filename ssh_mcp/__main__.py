"""SSH-LICCO MCP Server entry point for `python -m ssh_mcp`."""
from ssh_mcp.logging_config import suppress_known_warnings

suppress_known_warnings()

from ssh_mcp.server import run_server

run_server()