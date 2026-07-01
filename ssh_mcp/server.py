from __future__ import annotations

import asyncio
import logging
import os
from importlib.metadata import version as get_version
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .audit_logger import get_audit_logger
from .config_manager import ConfigManager
from .handlers import HANDLERS, schemas
from .handlers.context import HandlerContext
from .key_manager import KeyManager
from .session_manager import SessionManager
from .tunnel import Tunnel

try:
    __version__ = get_version("ssh-licco")
except Exception:
    from . import __version__

logger = logging.getLogger(__name__)


class SSHMCPServer:
    def __init__(self):
        self.server = Server("ssh-licco", __version__)
        self.session_manager = SessionManager()
        self.key_manager = KeyManager()
        self.config_manager = ConfigManager()
        self._env_config = self._load_env_config()
        self._logger = logger
        audit_path = os.getenv("SSH_AUDIT_LOG_PATH")
        self._audit = get_audit_logger(audit_path) if audit_path else None

        self._rate_limit_enabled = os.getenv("SSH_RATE_LIMIT", "true").lower() == "true"
        self._rate_limit_max = int(os.getenv("SSH_RATE_LIMIT_MAX", "30"))
        self._rate_limit_window = int(os.getenv("SSH_RATE_LIMIT_WINDOW", "60"))
        self._command_timestamps: list[float] = []

        # 活动的 SSH 本地端口转发隧道: local_port -> Tunnel
        self._tunnels: dict[int, "Tunnel"] = {}

        self._setup_handlers()

    @property
    def _ctx(self) -> HandlerContext:
        """Build a fresh context so tests can replace server attributes."""
        return HandlerContext(
            session_manager=self.session_manager,
            key_manager=self.key_manager,
            config_manager=self.config_manager,
            env_config=self._env_config,
            logger=self._logger,
            audit=self._audit,
            tunnels=self._tunnels,
        )

    def _load_env_config(self) -> dict:
        config: dict[str, Any] = {}
        if os.getenv("SSH_HOST"):
            config["host"] = os.getenv("SSH_HOST", "127.0.0.1")
            config["port"] = int(os.getenv("SSH_PORT", "22"))
            config["username"] = os.getenv("SSH_USER", "root")
            config["password"] = os.getenv("SSH_PASSWORD", "")
            config["timeout"] = int(os.getenv("SSH_TIMEOUT", "60"))
            config["keepalive_interval"] = int(os.getenv("SSH_KEEPALIVE_INTERVAL", "30"))
            config["session_timeout"] = int(os.getenv("SSH_SESSION_TIMEOUT", "7200"))
            config["client_type"] = os.getenv("SSH_CLIENT_TYPE", "paramiko")
            config["force_env_config"] = os.getenv("SSH_FORCE_ENV_CONFIG", "false").lower() == "true"
            config["sudo_password"] = os.getenv("SSH_SUDO_PASSWORD", "")
        return config

    def _check_rate_limit(self) -> tuple[bool, str]:
        if not self._rate_limit_enabled:
            return True, ""

        import time
        now = time.time()
        window_start = now - self._rate_limit_window
        self._command_timestamps = [ts for ts in self._command_timestamps if ts > window_start]

        if len(self._command_timestamps) >= self._rate_limit_max:
            return False, (
                f"⚠️ 频率限制触发：超过 {self._rate_limit_max} 次请求/{self._rate_limit_window}秒\n"
                f"请降低请求频率后重试。\n"
                f"可通过环境变量 SSH_RATE_LIMIT=false 临时禁用限制。"
            )

        self._command_timestamps.append(now)
        return True, ""

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return list(schemas.TOOLS.values())

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            allowed, msg = self._check_rate_limit()
            if not allowed:
                return [TextContent(type="text", text=msg)]

            try:
                handler = HANDLERS.get(name)
                if handler is None:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                return await handler(self._ctx, arguments)
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        import signal

        loop = asyncio.get_event_loop()
        shutdown_event = asyncio.Event()

        def signal_handler():
            shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                pass

        async with stdio_server() as (read_stream, write_stream):
            try:
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
            except (ConnectionError, BrokenPipeError):
                pass
            finally:
                # 关闭所有活动隧道
                for port, tunnel in list(self._tunnels.items()):
                    try:
                        tunnel.stop()
                    except Exception:
                        pass
                self._tunnels.clear()
                await self.session_manager.close_all_sessions()


async def main():
    server = SSHMCPServer()
    await server.run()


def run_server():
    import sys
    if not sys.stdin.isatty():
        print("Warning: Running in non-interactive mode (stdin is not a TTY)", file=sys.stderr)
        print("MCP server expects to be run as part of an MCP client", file=sys.stderr)
    # 加固点 1：运行账号最小权限（生产跳板机强制）
    # 仅当 SSH_RUNTIME_GUARD=true 时强制，否则仅打印警告。
    from .runtime_guard import enforce_runtime_guard
    enforce_runtime_guard()
    asyncio.run(main())


if __name__ == "__main__":
    run_server()