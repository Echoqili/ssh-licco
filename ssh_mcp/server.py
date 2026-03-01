from __future__ import annotations

import asyncio
from typing import Any
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .connection_config import ConnectionConfig
from .session_manager import SessionManager, SessionInfo
from .key_manager import KeyManager
from .config_manager import ConfigManager, SSHConfig, SSHHost


class SSHMCPServer:
    def __init__(self):
        self.server = Server("ssh-licco", "0.1.0")
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
            config["timeout"] = int(os.getenv("SSH_TIMEOUT", "30"))
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
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_config(self, args: dict) -> list[TextContent]:
        config = SSHConfig(
            host=args.get("host", "127.0.0.1"),
            port=args.get("port", 22),
            username=args.get("username", "root"),
            password=args.get("password", ""),
            timeout=args.get("timeout", 30)
        )
        self.config_manager.save(config)
        return [TextContent(
            type="text",
            text=f"SSH\u914d\u7f6e\u5df2\u4fdd\u5b58:\n"
                 f"\u4e3b\u673a: {config.host}:{config.port}\n"
                 f"\u7528\u6237\u540d: {config.username}\n"
                 f"\u914d\u7f6e\u6587\u4ef6: {self.config_manager.config_path}"
        )]

    async def _handle_login(self, args: dict) -> list[TextContent]:
        config_data = self.config_manager.load()
        if not config_data:
            return [TextContent(
                type="text",
                text="\u8bf7\u5148\u4f7f\u7528 ssh_config \u5de5\u5177\u914d\u7f6eSSH\u8fde\u63a5\u4fe1\u606f"
            )]
        
        if not config_data.password:
            return [TextContent(type="text", text="\u5bc6\u7801\u672a\u914d\u7f6e\uff0c\u8bf7\u5148\u4f7f\u7528 ssh_config \u8bbe\u7f6e\u5bc6\u7801")]
        
        config = ConnectionConfig(
            host=config_data.host,
            port=config_data.port,
            username=config_data.username,
            password=config_data.password,
            auth_method="password",
            timeout=config_data.timeout
        )
        
        session_info = await self.session_manager.create_session(config)
        
        output = f"SSH\u767b\u5f55\u6210\u529f!\n"
        output += f"\u4e3b\u673a: {session_info.host}:{session_info.port}\n"
        output += f"Session ID: {session_info.session_id}\n"
        output += f"\u7528\u6237\u540d: {session_info.username}\n"
        output += f"\u8fde\u63a5\u65f6\u95f4: {session_info.connected_at.isoformat()}"
        
        command = args.get("command")
        if command:
            session = await self.session_manager.get_session(session_info.session_id)
            result = await session.execute_command(command)
            output += f"\n\n--- \u547d\u4ee4\u8f93\u51fa ---\n"
            output += f"Exit Code: {result['exit_code']}\n"
            if result["stdout"]:
                output += f"\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n--- \u9519\u8bef ---\n{result['stderr']}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        host_config = None
        
        if args.get("name"):
            host_config = self.config_manager.get_host_by_name(args["name"])
            if not host_config:
                return [TextContent(type="text", text=f"Host '{args['name']}' not found in configuration files")]
        
        if not host_config and self._env_config:
            host_config = SSHHost(
                name="env-server",
                host=self._env_config.get("host", "127.0.0.1"),
                port=self._env_config.get("port", 22),
                username=self._env_config.get("username", "root"),
                password=self._env_config.get("password", ""),
                timeout=self._env_config.get("timeout", 30)
            )
        
        client_type = args.get("client_type") or self._env_config.get("client_type", "paramiko")
        
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
            output = f"\u2705 {result.get('message', 'Success')}"
            if "files" in result:
                output = f"\ud83d\udcc2 Files in {result.get('path', '.')}:\n"
                for f in result["files"]:
                    output += f"  - {f}\n"
        else:
            output = f"\u274c {result.get('message', 'Failed')}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_list_hosts(self, args: dict) -> list[TextContent]:
        hosts = self.config_manager.list_hosts()
        
        output = "Configured SSH Hosts:\n"
        
        if hosts:
            for host in hosts:
                output += f"\n- Name: {host.name}\n"
                output += f"  Host: {host.host}:{host.port}\n"
                output += f"  Username: {host.username}\n"
                output += f"  Password: {'***' if host.password else 'N/A'}\n"
        else:
            output += "\nNo hosts configured in config files.\n"
        
        if self._env_config:
            output += "\n--- Environment Variables ---\n"
            output += f"Host: {self._env_config.get('host', 'N/A')}\n"
            output += f"Port: {self._env_config.get('port', 22)}\n"
            output += f"Username: {self._env_config.get('username', 'N/A')}\n"
            output += f"Password: {'***' if self._env_config.get('password') else 'Not set'}\n"
        
        return [TextContent(type="text", text=output)]

    async def _handle_background_task(self, args: dict) -> list[TextContent]:
        """Handle background task execution for long-running commands like Docker build"""
        import uuid
        import os
        
        session_id = args.get("session_id")
        command = args.get("command")
        workdir = args.get("workdir", "/tmp")
        log_file = args.get("log_file", "/tmp/background_task.log")
        
        if not session_id or not command:
            return [TextContent(type="text", text="Error: session_id and command are required")]
        
        task_id = str(uuid.uuid4())[:8]
        
        background_command = f"""
cd {workdir} && nohup {command} > {log_file} 2>&1 &
echo $! > /tmp/task_{task_id}.pid
echo "Task started with PID: $(cat /tmp/task_{task_id}.pid)"
echo "Log file: {log_file}"
"""
        
        try:
            result = self.session_manager.execute_command(session_id, background_command, timeout=30)
            
            output = f"""�\ude80 Background Task Started!

Task ID: {task_id}
Command: {command}
Working Directory: {workdir}
Log File: {log_file}

Use ssh_task_status to check progress:
- Session ID: {session_id}
- Task ID: {task_id}

Example command:
  \u67e5\u770b\u4efb\u52a1\u72b6\u6001\uff0csession_id={session_id}\uff0ctask_id={task_id}
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
            check_pid_cmd = f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
            result = self.session_manager.execute_command(session_id, check_pid_cmd, timeout=10)
            status = result.get("stdout", "").strip()
            
            log_cmd = f"if [ -f {log_file} ]; then tail -20 {log_file}; else echo 'No log file yet'; fi"
            log_result = self.session_manager.execute_command(session_id, log_cmd, timeout=10)
            log_output = log_result.get("stdout", "")
            
            exit_code = None
            if status == "COMPLETED":
                exit_cmd = f"if [ -f {log_file} ]; then echo 'Exit code: 0 (check log for actual)'; else echo 'N/A'; fi"
                exit_result = self.session_manager.execute_command(session_id, exit_cmd, timeout=10)
                exit_code = exit_result.get("stdout", "")
            
            output = f"""\ud83d\udcca Task Status: {task_id}

Status: {status}

--- Recent Log Output ---
{log_output}

---
Use this command to check again:
  \u67e5\u770b\u4efb\u52a1\u72b6\u6001\uff0csession_id={session_id}\uff0ctask_id={task_id}
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
            
            output = f"""\ud83d\udc33 Docker Build Started!

Task ID: {task_id}
Image: {image_name}
Dockerfile: {dockerfile_path}
Context: {context}
Log File: {log_file}

Use ssh_docker_status to check progress:
  \u67e5\u770b Docker \u72b6\u6001\uff0csession_id={session_id}\uff0cimage_name={image_name}
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
            containers_cmd = "docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}'"
            containers_result = self.session_manager.execute_command(session_id, containers_cmd, timeout=10)
            
            output = "\ud83d\udc33 Docker Status\n\n"
            output += "--- Running Containers ---\n"
            output += containers_result.get("stdout", "No running containers\n")
            
            if image_name:
                images_cmd = f"docker images {image_name} --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'"
                images_result = self.session_manager.execute_command(session_id, images_cmd, timeout=10)
                output += "\n--- Docker Images ---\n"
                output += images_result.get("stdout", f"No images found matching {image_name}\n")
            
            log_files_cmd = "ls -la /tmp/docker_build_*.log 2>/dev/null | tail -5 || echo 'No build logs found'"
            log_result = self.session_manager.execute_command(session_id, log_files_cmd, timeout=10)
            output += "\n--- Recent Build Logs ---\n"
            output += log_result.get("stdout", "")
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error checking Docker status: {str(e)}")]

    async def run(self):
        import signal
        from contextlib import asynccontextmanager
        
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
                await self.session_manager.close_all_sessions()


async def main():
    server = SSHMCPServer()
    await server.run()


def run_server():
    """Synchronous entry point for CLI"""
    import sys
    
    if not sys.stdin.isatty():
        print("Warning: Running in non-interactive mode (stdin is not a TTY)", file=sys.stderr)
        print("MCP server expects to be run as part of an MCP client", file=sys.stderr)
    
    asyncio.run(main())


if __name__ == "__main__":
    run_server()
