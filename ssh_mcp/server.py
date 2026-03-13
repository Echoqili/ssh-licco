from __future__ import annotations

import asyncio
from typing import Any
from pathlib import Path
from importlib.metadata import version as get_version

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .connection_config import ConnectionConfig
from .session_manager import SessionManager, SessionInfo
from .key_manager import KeyManager
from .config_manager import ConfigManager, SSHConfig, SSHHost

try:
    __version__ = get_version("ssh-licco")
except Exception:
    from . import __version__


class SSHMCPServer:
    def __init__(self):
        self.server = Server("ssh-licco", __version__)
        self.session_manager = SessionManager()
        self.key_manager = KeyManager()
        self.config_manager = ConfigManager()
        self._env_config = self._load_env_config()
        self._setup_handlers()
    
    def _load_env_config(self) -> dict:
        """Load SSH configuration from environment variables."""
        import os
        config = {}
        if os.getenv("SSH_HOST"):
            config["host"] = os.getenv("SSH_HOST", "127.0.0.1")
            config["port"] = int(os.getenv("SSH_PORT", "22"))
            config["username"] = os.getenv("SSH_USER", "root")
            config["password"] = os.getenv("SSH_PASSWORD", "")
            config["timeout"] = int(os.getenv("SSH_TIMEOUT", "60"))
            config["keepalive_interval"] = int(os.getenv("SSH_KEEPALIVE_INTERVAL", "30"))
            config["session_timeout"] = int(os.getenv("SSH_SESSION_TIMEOUT", "7200"))
            config["client_type"] = os.getenv("SSH_CLIENT_TYPE", "paramiko")
        return config

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="ssh_config",
                    description="Configure SSH connection (host, port, username, password). Save to config file for easy login.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server IP or hostname", "default": "127.0.0.1"},
                            "port": {"type": "integer", "description": "SSH server port", "default": 22},
                            "username": {"type": "string", "description": "SSH username", "default": "root"},
                            "password": {"type": "string", "description": "SSH password"},
                            "timeout": {"type": "integer", "description": "Connection timeout (seconds)", "default": 30}
                        },
                        "required": ["password"]
                    }
                ),
                Tool(
                    name="ssh_login",
                    description="Login to SSH server using saved configuration (no parameters needed if config exists)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute after login (optional)"}
                        }
                    }
                ),
                Tool(
                    name="ssh_connect",
                    description="Establish an SSH connection to a remote server",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server hostname or IP (or use name to connect via server.json config)"},
                            "port": {"type": "integer", "description": "SSH server port (default: 22)", "default": 22},
                            "username": {"type": "string", "description": "SSH username"},
                            "password": {"type": "string", "description": "SSH password (optional if using key auth)"},
                            "private_key_path": {"type": "string", "description": "Path to private key file"},
                            "passphrase": {"type": "string", "description": "Passphrase for private key"},
                            "auth_method": {"type": "string", "enum": ["password", "private_key", "agent"], "default": "private_key"},
                            "name": {"type": "string", "description": "Connect using host from server.json by name"},
                            "client_type": {"type": "string", "enum": ["asyncssh"], "default": "asyncssh", "description": "SSH client implementation to use (only asyncssh supported)"}
                        }
                    }
                ),
                Tool(
                    name="ssh_list_hosts",
                    description="List all configured SSH hosts from server.json",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_execute",
                    description="Execute a command on an active SSH session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 30}
                        },
                        "required": ["session_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_disconnect",
                    description="Close an SSH session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID to close"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="ssh_list_sessions",
                    description="List all active SSH sessions",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_generate_key",
                    description="Generate a new SSH key pair",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key_type": {"type": "string", "enum": ["rsa", "ed25519"], "default": "ed25519"},
                            "key_size": {"type": "integer", "description": "Key size for RSA (default: 4096)", "default": 4096},
                            "comment": {"type": "string", "description": "Comment for the key"},
                            "save_path": {"type": "string", "description": "Path to save the key"}
                        }
                    }
                ),
                Tool(
                    name="ssh_file_transfer",
                    description="Transfer files via SFTP",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID"},
                            "local_path": {"type": "string", "description": "Local file path"},
                            "remote_path": {"type": "string", "description": "Remote file path"},
                            "direction": {"type": "string", "enum": ["upload", "download"], "description": "Transfer direction"}
                        },
                        "required": ["session_id", "local_path", "remote_path", "direction"]
                    }
                ),
                Tool(
                    name="ssh_background_task",
                    description="Execute long-running commands (like Docker build) in background with status polling. Returns task ID for polling.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "command": {"type": "string", "description": "Command to execute in background (e.g., docker build)"},
                            "workdir": {"type": "string", "description": "Working directory for the command", "default": "/tmp"},
                            "log_file": {"type": "string", "description": "Log file path", "default": "/tmp/background_task.log"}
                        },
                        "required": ["session_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_task_status",
                    description="Check status of background task (like Docker build progress)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "task_id": {"type": "string", "description": "Task ID returned from ssh_background_task"}
                        },
                        "required": ["session_id", "task_id"]
                    }
                ),
                Tool(
                    name="ssh_docker_build",
                    description="Build Docker image on remote server in background (solves timeout issues)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "dockerfile_path": {"type": "string", "description": "Path to Dockerfile (default: ./Dockerfile)", "default": "./Dockerfile"},
                            "image_name": {"type": "string", "description": "Docker image name and tag (e.g., myapp:latest)"},
                            "context": {"type": "string", "description": "Build context path (default: .)", "default": "."}
                        },
                        "required": ["session_id", "image_name"]
                    }
                ),
                Tool(
                    name="ssh_docker_status",
                    description="Check Docker build or container status on remote server",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "image_name": {"type": "string", "description": "Docker image name to check (optional)"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="ssh_add_host",
                    description="Add a new SSH server to config/hosts.json (for managing multiple servers)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Server name (e.g., 'production', 'dev-server')"},
                            "host": {"type": "string", "description": "Server hostname or IP"},
                            "port": {"type": "integer", "description": "SSH port", "default": 22},
                            "username": {"type": "string", "description": "SSH username", "default": "root"},
                            "password": {"type": "string", "description": "SSH password (optional)"},
                            "timeout": {"type": "integer", "description": "Connection timeout", "default": 60}
                        },
                        "required": ["name", "host"]
                    }
                ),
                Tool(
                    name="ssh_remove_host",
                    description="Remove an SSH server from config/hosts.json by name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Server name to remove"}
                        },
                        "required": ["name"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
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
                elif name == "ssh_docker_status":
                    return await self._handle_docker_status(arguments)
                elif name == "ssh_add_host":
                    return await self._handle_add_host(arguments)
                elif name == "ssh_remove_host":
                    return await self._handle_remove_host(arguments)
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
        config_data = self.config_manager.load()
        if not config_data:
            return [TextContent(
                type="text",
                text="请先使用 ssh_config 工具配置 SSH 连接信息"
            )]
        
        if not config_data.password:
            return [TextContent(type="text", text="密码未配置，请先使用 ssh_config 设置密码")]
        
        config = ConnectionConfig(
            host=config_data.host,
            port=config_data.port,
            username=config_data.username,
            password=config_data.password,
            auth_method="password",
            timeout=config_data.timeout
        )
        
        session_info = await self.session_manager.create_session(config)
        
        output = f"SSH 登录成功!\n"
        output += f"主机：{session_info.host}:{session_info.port}\n"
        output += f"Session ID: {session_info.session_id}\n"
        output += f"用户名：{session_info.username}\n"
        output += f"连接时间：{session_info.connected_at.isoformat()}"
        
        command = args.get("command")
        if command:
            session = await self.session_manager.get_session(session_info.session_id)
            result = await session.execute_command(command)
            output += f"\n\n--- 命令输出 ---\n"
            output += f"Exit Code: {result['exit_code']}\n"
            if result["stdout"]:
                output += f"\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n--- 错误 ---\n{result['stderr']}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        host_config = None
        
        # Priority 1: Use environment variable config from MCP server.json if configured
        if self._env_config and self._env_config.get("host"):
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
        
        # Priority 2: Try to get host from config/hosts.json by name
        if not host_config and args.get("name"):
            host_config = self.config_manager.get_host_by_name(args["name"])
            if not host_config:
                return [TextContent(type="text", text=f"Host '{args['name']}' not found in config/hosts.json")]
        
        # Priority 3: Use parameters from args if no env config or name provided
        if not host_config and args.get("host"):
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
        
        # Get client type from args, env config, or default to paramiko
        client_type = args.get("client_type") or self._env_config.get("client_type", "paramiko")
        
        # 隐藏密码显示
        password_display = "***" if host_config.password else "未设置"
        
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
                client_type=client_type
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
                auth_method=args.get("auth_method", "private_key"),
                timeout=args.get("timeout", 30),
                keepalive_interval=args.get("keepalive_interval", 30),
                session_timeout=args.get("session_timeout", 7200),
                client_type=client_type
            )
        
        session_info = await self.session_manager.create_session(config)
        
        return [TextContent(
            type="text",
            text=f"Successfully connected to {session_info.host}:{session_info.port}\n"
                 f"Session ID: {session_info.session_id}\n"
                 f"Username: {session_info.username}\n"
                 f"Keepalive Interval: {config.keepalive_interval}s\n"
                 f"Session Timeout: {config.session_timeout}s\n"
                 f"Connected at: {session_info.connected_at.isoformat()}"
        )]

    async def _handle_execute(self, args: dict) -> list[TextContent]:
        """处理命令执行（带安全验证）"""
        from .security import SecurityError, command_validator
        
        command = args.get("command")
        
        # 🔒 安全验证 - 防止任意命令执行
        try:
            command_validator.validate_command(command)
        except SecurityError as e:
            self._logger.error(f"Command blocked: {e}")
            return [TextContent(
                type="text",
                text=f"❌ 安全错误：{str(e)}"
            )]
        
        session = await self.session_manager.get_session(args["session_id"])
        if not session:
            return [TextContent(type="text", text=f"Session not found: {args['session_id']}")]
        
        timeout = args.get("timeout", 30)
        result = await session.execute_command(args["command"], timeout=timeout)
        
        output = f"Exit Code: {result['exit_code']}\n"
        if result["stdout"]:
            output += f"\n--- STDOUT ---\n{result['stdout']}"
        if result["stderr"]:
            output += f"\n--- STDERR ---\n{result['stderr']}"
        
        return [TextContent(type="text", text=output)]

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
        import os
        from .security import SecurityError, command_validator, path_validator
        
        session_id = args.get("session_id")
        command = args.get("command")
        workdir = args.get("workdir", "/tmp")
        log_file = args.get("log_file", "/tmp/background_task.log")
        
        if not session_id or not command:
            return [TextContent(type="text", text="Error: session_id and command are required")]
        
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
            result = self.session_manager.execute_command(session_id, background_command, timeout=30)
            
            output = f"""🚀 Background Task Started!

Task ID: {task_id}
Command: {command}
Working Directory: {safe_workdir}
Log File: {safe_log_file}

Use ssh_task_status to check progress:
- Session ID: {session_id}
- Task ID: {task_id}

Example command:
  查看任务状态，session_id={session_id}，task_id={task_id}
"""
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error starting background task: {str(e)}")]

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
            result = self.session_manager.execute_command(session_id, check_pid_cmd, timeout=10)
            status = result.get("stdout", "").strip()
            
            # Get recent log output
            log_cmd = f"if [ -f {log_file} ]; then tail -20 {log_file}; else echo 'No log file yet'; fi"
            log_result = self.session_manager.execute_command(session_id, log_cmd, timeout=10)
            log_output = log_result.get("stdout", "")
            
            # Get exit code if completed
            exit_code = None
            if status == "COMPLETED":
                exit_cmd = f"if [ -f {log_file} ]; then echo 'Exit code: 0 (check log for actual)'; else echo 'N/A'; fi"
                exit_result = self.session_manager.execute_command(session_id, exit_cmd, timeout=10)
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
        """Handle Docker build on remote server"""
        import uuid
        
        session_id = args.get("session_id")
        dockerfile_path = args.get("dockerfile_path", "./Dockerfile")
        image_name = args.get("image_name")
        context = args.get("context", ".")
        
        if not session_id or not image_name:
            return [TextContent(type="text", text="Error: session_id and image_name are required")]
        
        task_id = str(uuid.uuid4())[:8]
        log_file = f"/tmp/docker_build_{task_id}.log"
        
        docker_build_cmd = f"""
cd {context} && nohup docker build -t {image_name} -f {dockerfile_path} . > {log_file} 2>&1 &
echo $! > /tmp/docker_task_{task_id}.pid
echo "Docker build started"
"""
        
        try:
            result = self.session_manager.execute_command(session_id, docker_build_cmd, timeout=30)
            
            output = f"""🐳 Docker Build Started!

Task ID: {task_id}
Image: {image_name}
Dockerfile: {dockerfile_path}
Context: {context}
Log File: {log_file}

Use ssh_docker_status to check progress:
  查看 Docker 状态，session_id={session_id}，image_name={image_name}
"""
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error starting Docker build: {str(e)}")]

    async def _handle_docker_status(self, args: dict) -> list[TextContent]:
        """Check Docker build and container status"""
        
        session_id = args.get("session_id")
        image_name = args.get("image_name")
        
        if not session_id:
            return [TextContent(type="text", text="Error: session_id is required")]
        
        try:
            # Check running containers
            containers_cmd = "docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}'"
            containers_result = self.session_manager.execute_command(session_id, containers_cmd, timeout=10)
            
            output = "🐳 Docker Status\n\n"
            output += "--- Running Containers ---\n"
            output += containers_result.get("stdout", "No running containers\n")
            
            # Check images if requested
            if image_name:
                images_cmd = f"docker images {image_name} --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'"
                images_result = self.session_manager.execute_command(session_id, images_cmd, timeout=10)
                output += "\n--- Docker Images ---\n"
                output += images_result.get("stdout", f"No images found matching {image_name}\n")
            
            # Check Docker build logs if exists
            log_files_cmd = "ls -la /tmp/docker_build_*.log 2>/dev/null | tail -5 || echo 'No build logs found'"
            log_result = self.session_manager.execute_command(session_id, log_files_cmd, timeout=10)
            output += "\n--- Recent Build Logs ---\n"
            output += log_result.get("stdout", "")
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error checking Docker status: {str(e)}")]

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

    async def run(self):
        import signal
        from contextlib import asynccontextmanager
        
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
