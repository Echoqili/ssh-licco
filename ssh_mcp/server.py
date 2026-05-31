from __future__ import annotations

import asyncio
import logging
import os
import uuid
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .audit_logger import get_audit_logger
from .config_manager import ConfigManager, SSHConfig, SSHHost
from .connection_config import ConnectionConfig
from .key_manager import KeyManager
from .session_manager import SessionManager

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
        # 🔒 审计日志：初始化
        import os
        audit_path = os.getenv("SSH_AUDIT_LOG_PATH")
        self._audit = get_audit_logger(audit_path) if audit_path else None

        # 🔒 频率限制：防止 DoS 攻击（环境变量配置）
        self._rate_limit_enabled = os.getenv("SSH_RATE_LIMIT", "true").lower() == "true"
        self._rate_limit_max = int(os.getenv("SSH_RATE_LIMIT_MAX", "30"))  # 每时间窗口最大请求数
        self._rate_limit_window = int(os.getenv("SSH_RATE_LIMIT_WINDOW", "60"))  # 时间窗口（秒）
        self._command_timestamps: list[float] = []  # 命令执行时间戳记录

        self._setup_handlers()

    def _load_env_config(self) -> dict:
        """Load SSH configuration from environment variables."""
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
        return config

    def _check_rate_limit(self) -> tuple[bool, str]:
        """🔒 频率限制检查（滑动窗口算法）"""
        if not self._rate_limit_enabled:
            return True, ""

        import time
        now = time.time()
        window_start = now - self._rate_limit_window

        # 清理过期的请求记录
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
            return [
                Tool(
                    name="ssh_config",
                    description="Configure and save SSH connection settings (host, port, username, password) to local config file. Use this when you need to set up default SSH credentials for quick login without repeatedly entering connection details.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server IP address or hostname", "default": "127.0.0.1"},
                            "port": {"type": "integer", "description": "SSH server port number", "default": 22},
                            "username": {"type": "string", "description": "SSH login username", "default": "root"},
                            "password": {"type": "string", "description": "SSH login password (required)"},
                            "timeout": {"type": "integer", "description": "Connection timeout in seconds", "default": 30}
                        },
                        "required": ["password"]
                    }
                ),
                Tool(
                    name="ssh_login",
                    description="Quick login to SSH server using pre-saved configuration from ssh_config or MCP environment variables. Use this for simple, one-step login without specifying connection details. Optionally execute a command after login.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Optional command to execute immediately after successful login"}
                        }
                    }
                ),
                Tool(
                    name="ssh_connect",
                    description="Establish a new SSH connection to a remote server with explicit parameters. Use this when you need full control over connection settings (password/private key authentication, host key verification, etc.). Returns a session_id for subsequent commands.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server hostname or IP address (required unless 'name' is provided)"},
                            "port": {"type": "integer", "description": "SSH server port", "default": 22},
                            "username": {"type": "string", "description": "SSH username for authentication"},
                            "password": {"type": "string", "description": "SSH password for password-based authentication"},
                            "private_key_path": {"type": "string", "description": "Path to private key file for key-based authentication"},
                            "passphrase": {"type": "string", "description": "Passphrase for encrypted private key"},
                            "auth_method": {"type": "string", "enum": ["password", "private_key", "agent"], "default": "private_key", "description": "Authentication method to use"},
                            "name": {"type": "string", "description": "Use pre-configured host from hosts.json by name"},
                            "client_type": {"type": "string", "enum": ["asyncssh"], "default": "asyncssh", "description": "SSH client implementation"},
                            "strict_host_key_checking": {"type": "boolean", "default": True, "description": "Enable strict host key verification (recommended for security)"},
                            "known_hosts_path": {"type": "string", "description": "Path to known_hosts file"},
                            "accept_new_host_key": {"type": "boolean", "default": False, "description": "Auto-accept new host keys (for testing only)"}
                        }
                    }
                ),
                Tool(
                    name="ssh_list_hosts",
                    description="List all configured SSH hosts from hosts.json and MCP environment variables. Also shows password conflict detection results between different config sources.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_execute",
                    description="Execute a command on an active SSH session. Requires session_id from ssh_connect. Use background=True for long-running services like web servers that don't terminate immediately.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID obtained from ssh_connect or ssh_login (required)"},
                            "command": {"type": "string", "description": "Shell command to execute on remote server (required)"},
                            "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 30},
                            "background": {"type": "boolean", "description": "Run command in background without waiting for completion", "default": False}
                        },
                        "required": ["session_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_disconnect",
                    description="Close an active SSH session and release resources. Use this when finished working with a remote server to clean up connections.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID to disconnect (required)"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="ssh_list_sessions",
                    description="List all currently active SSH sessions with connection details including host, username, connection time, and activity status.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_generate_key",
                    description="Generate a new SSH key pair (RSA or Ed25519) for secure key-based authentication. Optionally save to a file path.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key_type": {"type": "string", "enum": ["rsa", "ed25519"], "default": "ed25519", "description": "Key algorithm type"},
                            "key_size": {"type": "integer", "description": "Key size for RSA (default: 4096)", "default": 4096},
                            "comment": {"type": "string", "description": "Optional comment to identify the key"},
                            "save_path": {"type": "string", "description": "Optional path to save the generated key files"}
                        }
                    }
                ),
                Tool(
                    name="ssh_file_transfer",
                    description="Transfer files between local and remote server via SFTP. Supports upload (local to remote) and download (remote to local) operations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Active SSH session ID (required)"},
                            "local_path": {"type": "string", "description": "Local file path (required)"},
                            "remote_path": {"type": "string", "description": "Remote file path (required)"},
                            "direction": {"type": "string", "enum": ["upload", "download"], "description": "Transfer direction (required)"}
                        },
                        "required": ["session_id", "local_path", "remote_path", "direction"]
                    }
                ),
                Tool(
                    name="ssh_background_task",
                    description="Execute long-running commands (like Docker build, compilation, or deployment) in background with status polling. Returns a task_id for monitoring progress. Use wait=True to block and wait for completion.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Active SSH session ID (required)"},
                            "command": {"type": "string", "description": "Command to execute in background (required)"},
                            "workdir": {"type": "string", "description": "Working directory for the command", "default": "/tmp"},
                            "log_file": {"type": "string", "description": "Path to log file for capturing output", "default": "/tmp/background_task.log"},
                            "wait": {"type": "boolean", "description": "Wait for task completion and return full output", "default": False},
                            "wait_timeout": {"type": "integer", "description": "Maximum wait time in seconds when wait=True", "default": 60}
                        },
                        "required": ["session_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_task_status",
                    description="Check the status and progress of a background task. Returns task state (running/completed/failed) and log output.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "SSH session ID (required)"},
                            "task_id": {"type": "string", "description": "Task ID from ssh_background_task (required)"}
                        },
                        "required": ["session_id", "task_id"]
                    }
                ),
                Tool(
                    name="ssh_docker_build",
                    description="Build Docker image on remote server in background mode to avoid timeout issues. Returns a task_id for monitoring build progress.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Active SSH session ID (required)"},
                            "dockerfile_path": {"type": "string", "description": "Path to Dockerfile", "default": "./Dockerfile"},
                            "image_name": {"type": "string", "description": "Docker image name and tag (e.g., myapp:latest) (required)"},
                            "context": {"type": "string", "description": "Build context directory", "default": "."}
                        },
                        "required": ["session_id", "image_name"]
                    }
                ),
                Tool(
                    name="ssh_add_host",
                    description="Add a new SSH server configuration to hosts.json file for easy management of multiple servers. Use ssh_connect with 'name' parameter to connect using this configuration.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Friendly name for the server (e.g., 'production', 'dev-server') (required)"},
                            "host": {"type": "string", "description": "Server hostname or IP address (required)"},
                            "port": {"type": "integer", "description": "SSH port number", "default": 22},
                            "username": {"type": "string", "description": "SSH login username", "default": "root"},
                            "password": {"type": "string", "description": "SSH password (optional for key auth)"},
                            "timeout": {"type": "integer", "description": "Connection timeout in seconds", "default": 60}
                        },
                        "required": ["name", "host"]
                    }
                ),
                Tool(
                    name="ssh_remove_host",
                    description="Remove an existing SSH server configuration from hosts.json by its friendly name.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Server name to remove (required)"}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="ssh_fallback_execute",
                    description="Execute a command on the remote server with automatic fallback priority (CLI → Paramiko). Use this when ssh_execute is blocked by security policy or when the AI does not have session-based tools available. This tool handles its own connection and does not require a prior ssh_login or ssh_connect.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute on the remote server (required)"},
                            "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 60}
                        },
                        "required": ["command"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            # 🔒 频率限制检查
            allowed, msg = self._check_rate_limit()
            if not allowed:
                return [TextContent(type="text", text=msg)]

            try:
                if name == "ssh_config":
                    return await self._handle_config(arguments)
                elif name == "ssh_login":
                    return await self._handle_login(arguments)
                elif name == "ssh_connect":
                    return await self._handle_connect(arguments)
                elif name == "ssh_execute":
                    return await self._handle_execute(arguments)
                elif name == "ssh_disconnect":
                    return await self._handle_disconnect(arguments)
                elif name == "ssh_list_sessions":
                    return await self._handle_list_sessions(arguments)
                elif name == "ssh_generate_key":
                    return await self._handle_generate_key(arguments)
                elif name == "ssh_file_transfer":
                    return await self._handle_file_transfer(arguments)
                elif name == "ssh_list_hosts":
                    return await self._handle_list_hosts(arguments)
                elif name == "ssh_background_task":
                    return await self._handle_background_task(arguments)
                elif name == "ssh_task_status":
                    return await self._handle_task_status(arguments)
                elif name == "ssh_docker_build":
                    return await self._handle_docker_build(arguments)
                elif name == "ssh_add_host":
                    return await self._handle_add_host(arguments)
                elif name == "ssh_remove_host":
                    return await self._handle_remove_host(arguments)
                elif name == "ssh_fallback_execute":
                    return await self._handle_fallback_execute(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_config(self, args: dict) -> list[TextContent]:
        import os
        # Use environment variable for password if not provided in args
        password = args.get("password")
        if not password:
            password = os.getenv("SSH_PASSWORD", "")

        config = SSHConfig(
            host=args.get("host", "127.0.0.1"),
            port=args.get("port", 22),
            username=args.get("username", "root"),
            password=password,
            timeout=args.get("timeout", 30)
        )
        self.config_manager.save(config)
        return [TextContent(
            type="text",
            text=f"SSH 配置已保存:\n"
                 f"主机：{config.host}:{config.port}\n"
                 f"用户名：{config.username}\n"
                 f"密码：{'已设置' if password else '未设置 (将使用环境变量 SSH_PASSWORD)'}\n"
                 f"配置文件：{self.config_manager.config_path}"
        )]

    async def _handle_login(self, args: dict) -> list[TextContent]:
        import os

        # 优先使用环境变量配置（如果设置了 SSH_HOST）
        if os.getenv("SSH_HOST"):
            self._logger.info("🔒 使用环境变量配置进行登录")
            config = ConnectionConfig(
                host=os.getenv("SSH_HOST", "127.0.0.1"),
                port=int(os.getenv("SSH_PORT", "22")),
                username=os.getenv("SSH_USER", "root"),
                password=os.getenv("SSH_PASSWORD", ""),
                auth_method="password" if os.getenv("SSH_PASSWORD") else "private_key",
                timeout=int(os.getenv("SSH_TIMEOUT", "60")),
                keepalive_interval=int(os.getenv("SSH_KEEPALIVE_INTERVAL", "30")),
                session_timeout=int(os.getenv("SSH_SESSION_TIMEOUT", "7200")),
                client_type=os.getenv("SSH_CLIENT_TYPE", "paramiko"),  # type: ignore[arg-type]
            )

            if not config.password:
                return [TextContent(type="text", text="❌ 错误：SSH_PASSWORD 环境变量未设置")]

            try:
                session_info = await self.session_manager.create_session(config)

                output = "SSH 登录成功!\n"
                output += f"主机：{session_info.host}:{session_info.port}\n"
                output += f"Session ID: {session_info.session_id}\n"
                output += f"用户名：{session_info.username}\n"
                output += f"连接时间：{session_info.connected_at.isoformat()}"

                command = args["command"]
                if command:
                    session = await self.session_manager.get_session(session_info.session_id)
                    result = await session.execute_command(command)
                    output += "\n\n--- 命令输出 ---\n"
                    output += f"Exit Code: {result['exit_code']}\n"
                    if result["stdout"]:
                        output += f"\n{result['stdout']}"
                    if result["stderr"]:
                        output += f"\n--- 错误 ---\n{result['stderr']}"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                return [TextContent(type="text", text=f"登录失败：{str(e)}")]

        # 环境变量未配置，使用保存的配置
        config_data = self.config_manager.load()
        if not config_data:
            return [TextContent(
                type="text",
                text="请先使用 ssh_config 工具配置 SSH 连接信息，或在 MCP 配置中设置环境变量"
            )]

        # 如果保存的密码为空，尝试使用环境变量
        password = config_data.password
        if not password:
            password = os.getenv("SSH_PASSWORD", "")

        if not password:
            return [TextContent(type="text", text="密码未配置，请先使用 ssh_config 设置密码或在 MCP 配置中设置 SSH_PASSWORD 环境变量")]

        config = ConnectionConfig(
            host=config_data.host,
            port=config_data.port,
            username=config_data.username,
            password=password,
            auth_method="password",
            timeout=config_data.timeout
        )

        session_info = await self.session_manager.create_session(config)

        output = "SSH 登录成功!\n"
        output += f"主机：{session_info.host}:{session_info.port}\n"
        output += f"Session ID: {session_info.session_id}\n"
        output += f"用户名：{session_info.username}\n"
        output += f"连接时间：{session_info.connected_at.isoformat()}"

        command = args.get("command")
        if command:
            session = await self.session_manager.get_session(session_info.session_id)
            result = await session.execute_command(command)
            output += "\n\n--- 命令输出 ---\n"
            output += f"Exit Code: {result['exit_code']}\n"
            if result["stdout"]:
                output += f"\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n--- 错误 ---\n{result['stderr']}"

        return [TextContent(type="text", text=output)]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        host_config = None

        # 检查是否启用了强制环境变量模式
        force_env = self._env_config.get("force_env_config", False)

        if force_env:
            # 🔒 强制模式：环境变量优先级最高
            self._logger.info("🔒 Using FORCE ENV CONFIG mode")
            if self._env_config and self._env_config.get("host"):
                host_config = SSHHost(
                    name="env-server-forced",
                    host=self._env_config.get("host", "127.0.0.1"),
                    port=self._env_config.get("port", 22),
                    username=self._env_config.get("username", "root"),
                    password=self._env_config.get("password", ""),
                    timeout=self._env_config.get("timeout", 30),
                    keepalive_interval=self._env_config.get("keepalive_interval", 30),
                    session_timeout=self._env_config.get("session_timeout", 7200)
                )
                self._logger.info(f"🔒 Forced environment host: {host_config.host}")
            else:
                # 环境变量未配置，回退到用户参数
                if args.get("host"):
                    host_config = SSHHost(
                        name="args-server",
                        host=args["host"],
                        port=args.get("port", 22),
                        username=args.get("username", "root"),
                        password=args.get("password", ""),
                        timeout=args.get("timeout", 30),
                        keepalive_interval=args.get("keepalive_interval", 30),
                        session_timeout=args.get("session_timeout", 7200)
                    )
                    self._logger.info(f"Using user-provided host (env not configured): {args['host']}")
        else:
            # ✅ 灵活模式：用户参数优先级最高（默认）
            # Priority 1: Use parameters from args (highest priority - user provided)
            if args.get("host"):
                host_config = SSHHost(
                    name="args-server",
                    host=args["host"],
                    port=args.get("port", 22),
                    username=args.get("username", "root"),
                    password=args.get("password", ""),
                    timeout=args.get("timeout", 30),
                    keepalive_interval=args.get("keepalive_interval", 30),
                    session_timeout=args.get("session_timeout", 7200)
                )
                self._logger.info(f"✅ Using user-provided host: {args['host']}")

            # Priority 2: Try to get host from config/hosts.json by name
            if not host_config and args.get("name"):
                host_config = self.config_manager.get_host_by_name(args["name"])
                if not host_config:
                    return [TextContent(type="text", text=f"Host '{args['name']}' not found in config/hosts.json")]
                self._logger.info(f"Using config file host: {host_config.host}")

            # Priority 3: Use environment variable config from MCP server.json (lowest priority - fallback)
            if not host_config and self._env_config and self._env_config.get("host"):
                host_config = SSHHost(
                    name="env-server",
                    host=self._env_config.get("host", "127.0.0.1"),
                    port=self._env_config.get("port", 22),
                    username=self._env_config.get("username", "root"),
                    password=self._env_config.get("password", ""),
                    timeout=self._env_config.get("timeout", 30),
                    keepalive_interval=self._env_config.get("keepalive_interval", 30),
                    session_timeout=self._env_config.get("session_timeout", 7200)
                )
                self._logger.info(f"Using environment variable host (fallback): {host_config.host}")

        # Debug log
        if host_config:
            self._logger.info(f"🎯 Final connection target: {host_config.host}:{host_config.port}")
            if force_env:
                self._logger.warning("🔒 FORCE MODE: Environment config overrides user parameters")
        else:
            self._logger.warning("No host configuration found!")

        # Get client type from args, env config, or default to paramiko
        client_type = args.get("client_type") or self._env_config.get("client_type", "paramiko")

        # 隐藏密码显示
        password_display = "***" if host_config and host_config.password else "未设置"

        if host_config:
            config = ConnectionConfig(
                host=host_config.host,
                port=host_config.port,
                username=host_config.username,
                password=host_config.password,
                auth_method="password" if host_config.password else "private_key",
                timeout=host_config.timeout,
                keepalive_interval=getattr(host_config, 'keepalive_interval', 30),
                session_timeout=getattr(host_config, 'session_timeout', 7200),
                client_type=client_type,
                strict_host_key_checking=args.get("strict_host_key_checking", True),
                known_hosts_path=args.get("known_hosts_path"),
                accept_new_host_key=args.get("accept_new_host_key", False),
            )
        else:
            # Use direct parameters from args
            config = ConnectionConfig(
                host=args["host"],
                port=args.get("port", 22),
                username=args["username"],
                password=args.get("password"),
                private_key_path=Path(args["private_key_path"]) if args.get("private_key_path") else None,
                passphrase=args.get("passphrase"),
                auth_method=args.get("auth_method"),  # Auto-detect if not provided
                timeout=args.get("timeout", 30),
                keepalive_interval=args.get("keepalive_interval", 30),
                session_timeout=args.get("session_timeout", 7200),
                client_type=client_type,
                strict_host_key_checking=args.get("strict_host_key_checking", True),
                known_hosts_path=args.get("known_hosts_path"),
                accept_new_host_key=args.get("accept_new_host_key", False),
            )

        try:
            session_info = await self.session_manager.create_session(config)

            # 🔒 审计日志：记录连接成功
            if self._audit:
                self._audit.log_connect(
                    username=config.username,
                    host=config.host,
                    port=config.port,
                    client_type=config.client_type,
                    session_id=session_info.session_id,
                    success=True
                )

            return [TextContent(
                type="text",
                text=f"Successfully connected to {session_info.host}:{session_info.port}\n"
                     f"Session ID: {session_info.session_id}\n"
                     f"Username: {session_info.username}\n"
                     f"Keepalive Interval: {config.keepalive_interval}s\n"
                     f"Session Timeout: {config.session_timeout}s\n"
                     f"Connected at: {session_info.connected_at.isoformat()}"
            )]
        except Exception as e:
            self._logger.error(f"Connection failed: {e}")

            # 🔒 审计日志：记录连接失败
            if self._audit:
                self._audit.log_connect(
                    username=config.username,
                    host=config.host,
                    port=config.port,
                    client_type=config.client_type,
                    success=False,
                    error_message=str(e)
                )

            return [TextContent(
                type="text",
                text=f"❌ 连接失败：{str(e)}\n\n"
                     f"请检查:\n"
                     f"1. 服务器地址和端口是否正确\n"
                     f"2. 用户名和密码/私钥是否正确\n"
                     f"3. 网络连接是否正常\n"
                     f"4. SSH 服务是否正在运行"
            )]

    async def _handle_execute(self, args: dict) -> list[TextContent]:
        """处理命令执行（带安全验证）"""
        from .security import SecurityError, command_validator

        command = args["command"]

        # 🔒 安全验证 - 防止任意命令执行
        try:
            command_validator.validate_command(command)
        except SecurityError as e:
            self._logger.error(f"Command blocked: {e}")

            # 🛑 暂停执行，提供交互式解决方案
            return [TextContent(
                type="text",
                text=f"""🛑 **命令被安全策略阻止**

**被阻止的命令**: `{command}`

**原因**: {str(e)}

---

## 🔧 解决方案

### 方式 1: 临时调整安全策略（推荐）

在下次请求前，通过环境变量调整安全策略：

```json
{{
  "mcpServers": {{
    "ssh": {{
      "command": "ssh-licco",
      "env": {{
        "SSH_SECURITY_LEVEL": "relaxed",
        "SSH_EXTRA_ALLOWED_COMMANDS": "被阻止的命令或字符"
      }}
    }}
  }}
}}
```

**可选安全级别**:
- `strict` - 严格模式（生产环境）
- `balanced` - 平衡模式（默认）
- `relaxed` - 宽松模式（开发/测试）

### 方式 2: 添加额外允许的字符

如果只是因为特殊字符（如 `|`, `&`, `;` 等）被阻止，可以添加：

```json
{{
  "SSH_EXTRA_ALLOWED_PATTERNS": "|,>,<,&,;"
}}
```

### 方式 3: 确认并继续（⚠️ 谨慎使用）

如果你确认该命令是安全的，可以：
1. 在 MCP 配置中设置 `SSH_SECURITY_LEVEL="relaxed"`
2. 重新执行该命令

---

**当前配置**:
- 安全级别：`{os.getenv('SSH_SECURITY_LEVEL', 'balanced')}`
- 额外允许命令：`{os.getenv('SSH_EXTRA_ALLOWED_COMMANDS', '无')}`

💡 **提示**: 修改配置后需要重启 MCP 服务器
"""
            )]

        session = await self.session_manager.get_session(args["session_id"])
        if not session:
            return [TextContent(type="text", text=f"Session not found: {args['session_id']}")]

        timeout = args.get("timeout", 30)
        background = args.get("background", None)

        # 🤖 自动判断是否需要后台执行
        if background is None:
            background = self._should_run_background(command)
            self._logger.info(f"Auto-detected background={background} for command: {command[:50]}...")

        result = await session.execute_command(args["command"], timeout=timeout, background=background)

        # 🔒 审计日志：记录命令执行
        if self._audit:
            import time
            exec_time = (time.time() - (args.get('_start_time') or time.time())) * 1000
            session_info = await self.session_manager.get_session(args["session_id"])
            self._audit.log_command(
                username=session_info.username if session_info else "unknown",
                host=session_info.host if session_info else "unknown",
                command=args["command"],
                return_code=result.get('exit_code', -1),
                stdout_length=len(result.get('stdout', '')),
                stderr_length=len(result.get('stderr', '')),
                session_id=args["session_id"],
                execution_time_ms=exec_time
            )

        if background:
            output = f"✅ Command started in background\n\n{result['stdout']}"
        else:
            output = f"Exit Code: {result['exit_code']}\n"
            if result["stdout"]:
                output += f"\n--- STDOUT ---\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n--- STDERR ---\n{result['stderr']}"

        return [TextContent(type="text", text=output)]

    def _should_run_background(self, command: str) -> bool:
        """自动判断命令是否应该后台执行
        
        检测可能导致阻塞的命令类型：
        1. Web 服务器启动命令
        2. 数据库服务启动命令
        3. 长时间运行的服务
        4. 监听端口的命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            bool: True 表示需要后台执行
        """
        command_lower = command.lower()

        # ❌ Docker 即时操作命令（不后台）
        docker_instant_commands = [
            'docker start ', 'docker stop ', 'docker restart ', 'docker rm ',
            'docker rmi ', 'docker pause ', 'docker unpause ', 'docker kill ',
            'docker commit ', 'docker export ', 'docker import ',
            'docker ps', 'docker images', 'docker logs', 'docker inspect',
            'docker stats', 'docker top', 'docker port', 'docker history',
            'docker pull', 'docker push', 'docker save', 'docker load',
            'docker network ls', 'docker volume ls', 'docker system',
            'docker exec', 'docker attach', 'docker cp',
        ]

        # 检查是否是 Docker 即时操作命令
        for cmd in docker_instant_commands:
            if cmd in command_lower:
                return False

        # Web 服务器
        web_servers = [
            'python app.py', 'python main.py', 'python manage.py runserver',
            'npm start', 'npm run serve', 'npm run dev',
            'yarn start', 'yarn serve', 'yarn dev',
            'node app.js', 'node server.js', 'node index.js',
            'flask run', 'django-admin runserver',
            'uvicorn', 'gunicorn', 'waitress-serve',
            'php artisan serve', 'php -S',
            'rails server', 'rails s',
            'go run', 'go build && ./',
        ]

        # 数据库服务
        database_servers = [
            'mongod', 'mysql', 'mysqld', 'postgres', 'postgresql',
            'redis-server', 'redis-server',
            'elasticsearch', 'kibana',
            'docker-compose up', 'docker run -d',
        ]

        # 开发服务器
        dev_servers = [
            'webpack-dev-server', 'webpack serve',
            'vite', 'vite dev', 'vite preview',
            'ng serve', 'angular serve',
            'next dev', 'nuxt dev',
            'svelte-kit dev',
        ]

        # 监听端口的命令模式
        listen_patterns = [
            '--host', '--port', '0.0.0.0', 'localhost:',
            '-p ', '--listen', '--bind',
        ]

        # 检查是否匹配已知的服务器命令
        for server_cmd in web_servers + database_servers + dev_servers:
            if server_cmd in command_lower:
                return True

        # 检查是否有监听端口的模式
        for pattern in listen_patterns:
            if pattern in command_lower:
                return True

        # 检查是否包含常见的服务器启动标志
        if any(flag in command for flag in ['--reload', '--debug', '--no-reload']):
            return True

        # 检查是否是守护进程或服务
        if 'systemctl start' in command or 'service start' in command:
            return True

        # 检查是否是后台任务队列
        if any(cmd in command_lower for cmd in ['celery', 'rq worker', 'sidekiq', 'resque']):
            return True

        # Java 相关命令
        java_patterns = [
            'java -jar', 'java -cp', 'java -class',
            'mvn spring-boot:run', 'mvn jetty:run', 'mvn tomcat:run',
            'gradle bootrun', 'gradle run', 'gradle apprun', 'gradle jettyrun',
            './mvnw spring-boot:run', './gradlew bootrun', './gradlew run',
            'java -server', 'java -x',
        ]

        # Java 应用服务器
        java_servers = [
            'tomcat', 'jetty', 'jboss', 'wildfly', 'websphere', 'weblogic',
            'glassfish', 'payara', 'liberty',
        ]

        # 检查 Java 命令
        for pattern in java_patterns:
            if pattern in command_lower:
                return True

        # 检查 Java 服务器
        for server in java_servers:
            if server in command_lower and ('start' in command_lower or 'run' in command_lower):
                return True

        # 检查是否有 java 关键字并且是启动/运行命令
        if 'java' in command_lower:
            if any(kw in command_lower for kw in ['start', 'run', 'launch', 'boot', 'server', 'daemon']):
                return True

        # Go 语言相关
        go_patterns = [
            'go run', 'go build && .', 'go install && ',
        ]
        for pattern in go_patterns:
            if pattern in command_lower:
                return True

        # Rust 相关
        rust_patterns = [
            'cargo run', 'cargo watch -x run', 'rustc --run',
        ]
        for pattern in rust_patterns:
            if pattern in command_lower:
                return True

        # Ruby 相关
        ruby_patterns = [
            'ruby app.rb', 'ruby server.rb', 'ruby lib/server.rb',
            'rails server', 'rails s', 'rake server',
            'puma', 'thin start', 'unicorn', 'passenger start',
            'rackup', 'shotgun',
        ]
        for pattern in ruby_patterns:
            if pattern in command_lower:
                return True

        # PHP 相关（除了 artisan）
        php_patterns = [
            'php -S', 'php -s', 'php server', 'php -t',
            'laravel serve', 'symfony server:start', 'symfony serve',
        ]
        for pattern in php_patterns:
            if pattern in command_lower:
                return True

        # .NET/C# 相关
        dotnet_patterns = [
            'dotnet run', 'dotnet watch run', 'dotnet webserver',
            ' kestrel', ' iisexpress',
        ]
        for pattern in dotnet_patterns:
            if pattern in command_lower:
                return True

        # Scala 相关
        scala_patterns = [
            'sbt run', 'sbt ~run', 'scala -howtorun:object',
        ]
        for pattern in scala_patterns:
            if pattern in command_lower:
                return True

        # Elixir 相关
        elixir_patterns = [
            'mix phx.server', 'mix phx.server',
            'iex -s mix', 'iex --sname', 'iex -S',
            'elixir --sname', 'elixir -e',
        ]
        for pattern in elixir_patterns:
            if pattern in command_lower:
                return True

        # Erlang 相关
        erlang_patterns = [
            'erl -sname', 'erl -name', 'rebar3 shell',
        ]
        for pattern in erlang_patterns:
            if pattern in command_lower:
                return True

        # Haskell 相关
        haskell_patterns = [
            'stack exec', 'cabal run', 'ghci',
        ]
        for pattern in haskell_patterns:
            if pattern in command_lower:
                return True

        # Clojure 相关
        clojure_patterns = [
            'lein run', 'lein ring server', 'boot run',
        ]
        for pattern in clojure_patterns:
            if pattern in command_lower:
                return True

        # R 语言相关
        r_patterns = [
            'rserve', 'rserver', 'shiny::runapp', 'shiny run',
        ]
        for pattern in r_patterns:
            if pattern in command_lower:
                return True

        # 其他服务器/框架
        other_servers = [
            'nginx', 'apache', 'httpd', 'caddy',
            'haproxy', 'traefik', 'envoy',
            'prometheus', 'grafana-server', 'telegraf',
            'consul', 'vault', 'nomad',
        ]
        for server in other_servers:
            if server in command_lower:
                return True

        return False

    async def _handle_disconnect(self, args: dict) -> list[TextContent]:
        session_id = args["session_id"]
        await self.session_manager.close_session(session_id)
        return [TextContent(type="text", text=f"Session {session_id} closed")]

    async def _handle_list_sessions(self, args: dict) -> list[TextContent]:
        sessions = self.session_manager.list_sessions()

        if not sessions:
            return [TextContent(type="text", text="No active sessions")]

        output = "Active Sessions:\n"
        for session in sessions:
            output += f"\n- Session ID: {session.session_id}\n"
            output += f"  Host: {session.host}:{session.port}\n"
            output += f"  Username: {session.username}\n"
            output += f"  State: {session.state.value}\n"
            output += f"  Connected: {session.connected_at.isoformat()}\n"
            output += f"  Last Activity: {session.last_activity.isoformat()}\n"
            output += f"  Last Keepalive: {session.last_keepalive.isoformat()}\n"

        return [TextContent(type="text", text=output)]

    async def _handle_generate_key(self, args: dict) -> list[TextContent]:
        key_type = args.get("key_type", "ed25519")
        key_size = args.get("key_size", 4096)
        comment = args.get("comment")
        save_path = args.get("save_path")

        if key_type == "rsa":
            key_pair = self.key_manager.generate_rsa_key(key_size=key_size, comment=comment)
        else:
            key_pair = self.key_manager.generate_ed25519_key(comment=comment)

        if save_path:
            key_path = Path(save_path)
            self.key_manager.save_key(key_pair, key_path)

        return [TextContent(
            type="text",
            text=f"Generated {key_type} key pair\n"
                 f"Fingerprint: {key_pair.fingerprint}\n"
                 f"Public Key:\n{key_pair.public_key}\n"
                 f"{'Saved to: ' + save_path if save_path else 'Key not saved (provide save_path to persist)'}"
        )]

    async def _handle_file_transfer(self, args: dict) -> list[TextContent]:
        session = await self.session_manager.get_session(args["session_id"])
        if not session:
            return [TextContent(type="text", text=f"Session not found: {args['session_id']}")]

        direction = args.get("direction", "upload")
        local_path = args.get("local_path", "")
        remote_path = args.get("remote_path", "")

        if direction == "upload":
            result = await session.upload_file(local_path, remote_path)
        elif direction == "download":
            result = await session.download_file(remote_path, local_path)
        elif direction == "list":
            result = await session.list_directory(remote_path or ".")
        else:
            return [TextContent(type="text", text=f"Unknown direction: {direction}")]

        if result.get("success"):
            output = f"✅ {result.get('message', 'Success')}"
            if "files" in result:
                output = f"📁 Files in {result.get('path', '.')}:\n"
                for f in result["files"]:
                    output += f"  - {f}\n"
        else:
            output = f"❌ {result.get('message', 'Failed')}"

        return [TextContent(type="text", text=output)]

    async def _handle_list_hosts(self, args: dict) -> list[TextContent]:
        hosts = self.config_manager.list_hosts()

        output = "📋 SSH 服务器配置列表\n\n"

        # Priority 1: Environment variable config from MCP server.json
        if self._env_config and self._env_config.get("host"):
            output += "🔹 [优先级 1] MCP 配置文件 (mcp.json)\n"
            output += f"  主机：{self._env_config.get('host')}:{self._env_config.get('port', 22)}\n"
            output += f"  用户：{self._env_config.get('username')}\n"
            output += f"  密码：{'***' if self._env_config.get('password') else '未设置'}\n"
            output += f"  超时：{self._env_config.get('timeout', 30)}s\n\n"

            # 🔍 检测密码冲突
            output += "🔍 配置冲突检测:\n"
            env_host = self._env_config.get('host')
            env_user = self._env_config.get('username')
            env_password = self._env_config.get('password')

            conflict_found = False
            if hosts:
                for host in hosts:
                    if host.host == env_host and host.username == env_user:
                        if host.password and env_password and host.password != env_password:
                            output += "  ❌ 发现密码冲突!\n"
                            output += f"     主机：{host.host}\n"
                            output += f"     MCP 配置密码：{'已设置'} (已脱敏)\n"
                            output += f"     hosts.json 密码：{'已设置'} (已脱敏)\n"
                            output += "  💡 建议：统一两个配置文件中的密码，或使用 SSH_FORCE_ENV_CONFIG=true 强制使用环境变量\n"
                            conflict_found = True
                            break

            if not conflict_found:
                output += "  ✅ 未检测到密码冲突\n"
            output += "\n"

        # Priority 2: Hosts from config/hosts.json
        output += "🔹 [优先级 2] 本地配置文件 (config/hosts.json)\n"
        if hosts:
            for i, host in enumerate(hosts, 1):
                output += f"\n  {i}. {host.name}\n"
                output += f"     主机：{host.host}:{host.port}\n"
                output += f"     用户：{host.username}\n"
                output += f"     密码：{'***' if host.password else '未设置'}\n"
                output += f"     超时：{host.timeout}s\n"
        else:
            output += "  (空)\n"
            output += "  💡 提示：使用 '添加 SSH 服务器' 命令来添加新服务器\n"

        return [TextContent(type="text", text=output)]

    async def _handle_background_task(self, args: dict) -> list[TextContent]:
        """Handle background task execution for long-running commands like Docker build (带安全限制)"""
        import uuid

        from .security import SecurityError, command_validator, path_validator

        session_id = args.get("session_id")
        command = args.get("command")
        workdir = args.get("workdir", "/tmp")
        log_file = args.get("log_file", "/tmp/background_task.log")
        wait = args.get("wait", False)  # ← 新增：等待任务完成
        wait_timeout = args.get("wait_timeout", 60)  # ← 新增：等待超时（秒）

        if not session_id or not command:
            return [TextContent(type="text", text="Error: session_id and command are required")]

        # ❌ 检查是否是不适合后台执行的命令
        instant_commands = [
            'docker start ', 'docker stop ', 'docker restart ', 'docker rm ',
            'docker rmi ', 'docker pause ', 'docker unpause ', 'docker kill ',
            'docker ps', 'docker images', 'docker logs', 'docker inspect',
            'docker exec', 'docker attach', 'docker cp',
            'git status', 'git log', 'git diff',
            'ls ', 'cat ', 'tail ', 'head ', 'grep ',
            'pwd', 'whoami', 'date', 'echo ',
        ]

        for cmd in instant_commands:
            if cmd in command.lower():
                return [TextContent(
                    type="text",
                    text=f"""❌ **命令不适合后台执行**

**被阻止的命令**: `{command}`

**原因**: 该命令是即时操作，不需要后台执行

**建议**: 请使用 `ssh_execute` 工具执行此命令

**示例**:
```python
ssh_execute({{
  "session_id": "{session_id}",
  "command": "{command}"
}})
```

**适合后台执行的命令**:
- ✅ Docker 构建：`docker build -t image .`
- ✅ 启动服务：`python app.py`, `npm start`
- ✅ 长时间运行的任务：`docker-compose up`
"""
                )]

        # 🔒 安全验证：命令
        try:
            command_validator.validate_command(command.split()[0] if command.split() else "")
        except SecurityError as e:
            self._logger.error(f"Background task command blocked: {e}")
            return [TextContent(
                type="text",
                text=f"❌ 安全错误：{str(e)}"
            )]

        # 🔒 安全验证：工作目录
        try:
            safe_workdir = str(path_validator.validate_path(workdir))
        except SecurityError as e:
            self._logger.error(f"Background task workdir blocked: {e}")
            return [TextContent(
                type="text",
                text=f"❌ 安全错误：工作目录不被允许 - {str(e)}"
            )]

        # 🔒 安全验证：日志文件路径
        try:
            safe_log_file = str(path_validator.validate_path(log_file))
        except SecurityError as e:
            self._logger.error(f"Background task log file blocked: {e}")
            return [TextContent(
                type="text",
                text=f"❌ 安全错误：日志文件路径不被允许 - {str(e)}"
            )]

        # 🔒 限制：检查命令中是否包含危险操作
        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:', 'chmod -R 777 /']
        for pattern in dangerous_patterns:
            if pattern in command:
                return [TextContent(
                    type="text",
                    text=f"❌ 安全错误：命令包含危险操作 '{pattern}'"
                )]

        # Create a unique task ID
        task_id = str(uuid.uuid4())[:8]

        # Wrap command to run in background with logging
        # Use nohup and redirect output to log file
        background_command = f"""
cd {safe_workdir} && nohup {command} > {safe_log_file} 2>&1 &
echo $! > /tmp/task_{task_id}.pid
echo "Task started with PID: $(cat /tmp/task_{task_id}.pid)"
echo "Log file: {safe_log_file}"
"""

        try:
            # 启动后台任务（使用后台模式）
            result = await self.session_manager.execute_command(session_id, background_command, timeout=30, background=True)

            # 🤖 如果设置了 wait 参数，等待任务完成
            if wait:
                output = await self._wait_for_task_completion(
                    session_id=session_id,
                    task_id=task_id,
                    log_file=safe_log_file,
                    timeout=wait_timeout
                )
            else:
                output = f"""🚀 Background Task Started!

✅ Task ID: {task_id}
📝 Command: {command}
📂 Working Directory: {safe_workdir}
📄 Log File: {safe_log_file}

---

💡 **重要提示**:
- 任务已在后台运行，**无需持续检查状态**
- 如需查看进度，请**直接使用 ssh_execute 工具**执行以下命令：

**查看实时日志** (推荐):
```bash
ssh_execute(session_id="{session_id}", command="tail -f {safe_log_file}")
```

**查看完整日志**:
```bash
ssh_execute(session_id="{session_id}", command="cat {safe_log_file}")
```

**检查进程状态** (可选):
```bash
ssh_execute(session_id="{session_id}", command="ps -p $(cat /tmp/task_{task_id}.pid) -o pid,stat,time,command")
```

---

⚠️ **注意**: 
- 请避免频繁调用检查工具，建议等待 30-60 秒后再查看日志
- **不要使用 ssh_background_task 查看日志**，该工具仅用于启动后台任务
"""

            return [TextContent(type="text", text=output)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error starting background task: {str(e)}")]

    async def _wait_for_task_completion(self, session_id: str, task_id: str, log_file: str, timeout: int) -> str:
        """等待后台任务完成并返回结果"""
        import asyncio

        pid_file = f"/tmp/task_{task_id}.pid"
        elapsed = 0
        interval = 2  # 每 2 秒检查一次

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            # 检查进程是否还在运行
            check_cmd = f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
            result = await self.session_manager.execute_command(session_id, check_cmd, timeout=10)
            status = result.get("stdout", "").strip()

            if status == "COMPLETED" or status == "NOT_FOUND":
                # 任务完成，读取日志
                log_cmd = f"if [ -f {log_file} ]; then cat {log_file}; else echo 'No log file found'; fi"
                log_result = await self.session_manager.execute_command(session_id, log_cmd, timeout=10)
                log_content = log_result.get("stdout", "")

                return f"""✅ Task Completed!

📊 Task ID: {task_id}
⏱️  Execution Time: ~{elapsed} seconds
📄 Log File: {log_file}

---

📝 **Command Output**:
{log_content}

---

💡 **提示**: 任务已完成，可以继续下一步操作
"""

        # 超时，返回当前状态
        return f"""⏱️ Task Still Running (Timeout)

📊 Task ID: {task_id}
⏱️  Waited: {elapsed} seconds (timeout: {timeout}s)
📄 Log File: {log_file}

---

💡 **提示**: 任务仍在运行中，请使用 ssh_execute 查看日志：
```bash
ssh_execute(session_id="{session_id}", command="cat {log_file}")
```
"""

    async def _handle_task_status(self, args: dict) -> list[TextContent]:
        """Check status of background task"""

        session_id = args.get("session_id")
        task_id = args.get("task_id")

        if not session_id or not task_id:
            return [TextContent(type="text", text="Error: session_id and task_id are required")]

        pid_file = f"/tmp/task_{task_id}.pid"
        log_file = "/tmp/background_task.log"

        try:
            # Check if process is still running
            check_pid_cmd = f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
            result = await self.session_manager.execute_command(session_id, check_pid_cmd, timeout=10)
            status = result.get("stdout", "").strip()

            # Get recent log output
            log_cmd = f"if [ -f {log_file} ]; then tail -20 {log_file}; else echo 'No log file yet'; fi"
            log_result = await self.session_manager.execute_command(session_id, log_cmd, timeout=10)
            log_output = log_result.get("stdout", "")

            # Get exit code if completed
            exit_code = None
            if status == "COMPLETED":
                exit_cmd = f"if [ -f {log_file} ]; then echo 'Exit code: 0 (check log for actual)'; else echo 'N/A'; fi"
                exit_result = await self.session_manager.execute_command(session_id, exit_cmd, timeout=10)
                exit_code = exit_result.get("stdout", "")

            output = f"""📊 Task Status: {task_id}

Status: {status}

--- Recent Log Output ---
{log_output}

---
Use this command to check again:
  查看任务状态，session_id={session_id}，task_id={task_id}
"""
            return [TextContent(type="text", text=output)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error checking task status: {str(e)}")]

    async def _handle_docker_build(self, args: dict) -> list[TextContent]:
        """Handle Docker build on remote server using background task"""

        session_id = args.get("session_id")
        dockerfile_path = args.get("dockerfile_path", "./Dockerfile")
        image_name = args.get("image_name")
        context = args.get("context", ".")

        if not session_id or not image_name:
            return [TextContent(type="text", text="Error: session_id and image_name are required")]

        task_id = str(uuid.uuid4())[:8]
        log_file = f"/tmp/docker_build_{task_id}.log"

        # 构建 Docker 命令
        docker_build_cmd = f"cd {context} && docker build -t {image_name} -f {dockerfile_path} ."

        # 使用后台任务执行 Docker 构建
        background_args = {
            "session_id": session_id,
            "command": docker_build_cmd,
            "workdir": context,
            "log_file": log_file
        }

        # 调用后台任务处理
        return await self._handle_background_task(background_args)

    async def _handle_add_host(self, args: dict) -> list[TextContent]:
        """Add a new SSH server to config/hosts.json"""
        from .config_manager import SSHHost

        name = args.get("name")
        host = args.get("host")
        port = args.get("port", 22)
        username = args.get("username", "root")
        password = args.get("password", "")
        timeout = args.get("timeout", 60)

        if not name or not host:
            return [TextContent(type="text", text="❌ 错误：name 和 host 是必填参数")]

        # Create new host entry
        new_host = SSHHost(
            name=name,
            host=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            keepalive_interval=30,
            session_timeout=7200
        )

        # Add to config
        self.config_manager.add_host(new_host)

        return [TextContent(
            type="text",
            text=f"✅ SSH 服务器已添加!\n\n"
                 f"名称：{name}\n"
                 f"主机：{host}:{port}\n"
                 f"用户：{username}\n"
                 f"超时：{timeout}s\n\n"
                 f"💡 使用 '连接 SSH' 命令时指定 name='{name}' 来连接此服务器"
        )]

    async def _handle_remove_host(self, args: dict) -> list[TextContent]:
        """Remove an SSH server from config/hosts.json"""
        name = args.get("name")

        if not name:
            return [TextContent(type="text", text="❌ 错误：需要提供服务器名称")]

        # Remove from config
        if self.config_manager.remove_host(name):
            return [TextContent(
                type="text",
                text=f"✅ SSH 服务器 '{name}' 已删除"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ 未找到名为 '{name}' 的服务器"
            )]

    async def _handle_fallback_execute(self, args: dict) -> list[TextContent]:
        """使用自动降级执行远程命令 (CLI → Paramiko)"""
        from .fallback_executor import FallbackExecutor, create_fallback_executor_from_env

        command = args.get("command", "")
        timeout = args.get("timeout", 60)

        if not command:
            return [TextContent(type="text", text="❌ 错误：需要提供 command")]

        try:
            executor = create_fallback_executor_from_env()

            self._logger.info(
                "Fallback execute: CLI available={}, command={}".format(
                    executor.check_cli_available(), command
                )
            )

            result = executor.execute(command, timeout=timeout)
            output = FallbackExecutor.format_result(result)

            method_used = result.get("method", "unknown")
            exit_code = result.get("exit_code", -1)

            if result.get("stderr"):
                self._logger.warning(
                    "Fallback execute stderr (method={}): {}".format(
                        method_used, result["stderr"][:200]
                    )
                )

            return [TextContent(type="text", text=output)]
        except Exception as e:
            self._logger.error("Fallback execute failed: {}".format(e))
            return [TextContent(type="text", text="❌ 执行失败: {}".format(e))]

    async def run(self):
        import signal

        # 设置信号处理器用于优雅关闭
        loop = asyncio.get_event_loop()
        shutdown_event = asyncio.Event()

        def signal_handler():
            shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows 不支持 add_signal_handler，使用替代方案
                pass

        async with stdio_server() as (read_stream, write_stream):
            try:
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
            except (ConnectionError, BrokenPipeError):
                # 客户端断开连接时优雅退出
                pass
            finally:
                await self.session_manager.close_all_sessions()


async def main():
    server = SSHMCPServer()
    await server.run()


def run_server():
    """Synchronous entry point for CLI"""
    import sys

    # 检查是否在非交互模式运行（如 Docker 构建）
    if not sys.stdin.isatty():
        # 在非交互模式下，添加超时保护
        print("Warning: Running in non-interactive mode (stdin is not a TTY)", file=sys.stderr)
        print("MCP server expects to be run as part of an MCP client", file=sys.stderr)

    asyncio.run(main())


if __name__ == "__main__":
    run_server()
