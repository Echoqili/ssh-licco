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
        import os
        audit_path = os.getenv("SSH_AUDIT_LOG_PATH")
        self._audit = get_audit_logger(audit_path) if audit_path else None

        self._rate_limit_enabled = os.getenv("SSH_RATE_LIMIT", "true").lower() == "true"
        self._rate_limit_max = int(os.getenv("SSH_RATE_LIMIT_MAX", "30"))
        self._rate_limit_window = int(os.getenv("SSH_RATE_LIMIT_WINDOW", "60"))
        self._command_timestamps: list[float] = []

        self._setup_handlers()

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
            return [
                Tool(
                    name="ssh_connect",
                    description="Establish an SSH connection to a remote server. If no parameters are provided, auto-connects using environment variables or saved config. Supports password, private key, and agent authentication. Optionally save the config and/or execute a command after connecting.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server hostname or IP. If omitted, auto-reads from env vars or saved config."},
                            "port": {"type": "integer", "description": "SSH port", "default": 22},
                            "username": {"type": "string", "description": "SSH username. If omitted, auto-reads from env vars."},
                            "password": {"type": "string", "description": "SSH password for password-based auth."},
                            "private_key_path": {"type": "string", "description": "Path to private key file for key-based auth."},
                            "passphrase": {"type": "string", "description": "Passphrase for encrypted private key."},
                            "auth_method": {"type": "string", "enum": ["password", "private_key", "agent"], "default": "private_key", "description": "Authentication method."},
                            "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name."},
                            "save_config": {"type": "boolean", "description": "Save connection settings to local config file for future use.", "default": False},
                            "command": {"type": "string", "description": "Optional command to execute immediately after connecting."},
                            "accept_new_host_key": {"type": "boolean", "default": True, "description": "Auto-accept new host keys."}
                        }
                    }
                ),
                Tool(
                    name="ssh_execute",
                    description="Execute a command on a remote server. If session_id is omitted, auto-connects using environment variables. Supports background execution for long-running tasks (auto-detected or manual). Use background=True for web servers, Docker builds, compilations, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect. If omitted, auto-connects via env vars."},
                            "command": {"type": "string", "description": "Shell command to execute on the remote server (required)."},
                            "timeout": {"type": "integer", "description": "Command timeout in seconds.", "default": 30},
                            "background": {"type": "boolean", "description": "Run in background for long-running tasks. Auto-detected if not specified."},
                            "workdir": {"type": "string", "description": "Working directory for background tasks.", "default": "/tmp"},
                            "log_file": {"type": "string", "description": "Log file path for background task output.", "default": "/tmp/background_task.log"},
                            "wait": {"type": "boolean", "description": "Wait for background task to complete.", "default": False},
                            "wait_timeout": {"type": "integer", "description": "Max wait time in seconds when wait=True.", "default": 60}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="ssh_disconnect",
                    description="Close an active SSH session. If no session_id is provided, lists all currently active sessions with connection details.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID to disconnect. If omitted, lists all active sessions."}
                        }
                    }
                ),
                Tool(
                    name="ssh_file_transfer",
                    description="Transfer files between local and remote server via SFTP. Supports upload, download, and directory listing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Active SSH session ID (required)."},
                            "local_path": {"type": "string", "description": "Local file path (required)."},
                            "remote_path": {"type": "string", "description": "Remote file path (required)."},
                            "direction": {"type": "string", "enum": ["upload", "download", "list"], "description": "Transfer direction: upload, download, or list directory."}
                        },
                        "required": ["session_id", "local_path", "remote_path", "direction"]
                    }
                ),
                Tool(
                    name="ssh_host",
                    description="Manage SSH server configurations in hosts.json. Use action=list to view all hosts, action=add to register a new server, action=remove to delete a server.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["list", "add", "remove"], "description": "Action: list all hosts, add a new host, or remove a host."},
                            "name": {"type": "string", "description": "Friendly name for the server. Required for add and remove."},
                            "host": {"type": "string", "description": "Server hostname or IP. Required for add."},
                            "port": {"type": "integer", "description": "SSH port number.", "default": 22},
                            "username": {"type": "string", "description": "SSH login username.", "default": "root"},
                            "password": {"type": "string", "description": "SSH password (optional for key auth)."},
                            "timeout": {"type": "integer", "description": "Connection timeout in seconds.", "default": 60}
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="ssh_docker",
                    description="Manage Docker on the remote server. Supports ps (list containers), images (list images), build (build an image in background), and logs (view container logs).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Active SSH session ID (required)."},
                            "action": {"type": "string", "enum": ["ps", "images", "build", "logs"], "description": "Docker action: ps=list containers, images=list images, build=build an image, logs=view container logs."},
                            "image_name": {"type": "string", "description": "Docker image name. Required for build, optional filter for images."},
                            "container_name": {"type": "string", "description": "Container name or ID. Required for logs."},
                            "dockerfile_path": {"type": "string", "description": "Path to Dockerfile for build.", "default": "./Dockerfile"},
                            "context": {"type": "string", "description": "Build context directory for build.", "default": "."},
                            "tail": {"type": "integer", "description": "Number of log lines to retrieve.", "default": 100}
                        },
                        "required": ["session_id", "action"]
                    }
                ),
                Tool(
                    name="ssh_generate_key",
                    description="Generate a new SSH key pair (RSA or Ed25519) for secure key-based authentication. Optionally save to a file path.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key_type": {"type": "string", "enum": ["rsa", "ed25519"], "default": "ed25519", "description": "Key algorithm type."},
                            "key_size": {"type": "integer", "description": "Key size for RSA.", "default": 4096},
                            "comment": {"type": "string", "description": "Optional comment to identify the key."},
                            "save_path": {"type": "string", "description": "Optional path to save the generated key files."}
                        }
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            allowed, msg = self._check_rate_limit()
            if not allowed:
                return [TextContent(type="text", text=msg)]

            try:
                if name == "ssh_connect":
                    return await self._handle_connect(arguments)
                elif name == "ssh_execute":
                    return await self._handle_execute(arguments)
                elif name == "ssh_disconnect":
                    return await self._handle_disconnect(arguments)
                elif name == "ssh_file_transfer":
                    return await self._handle_file_transfer(arguments)
                elif name == "ssh_host":
                    return await self._handle_host(arguments)
                elif name == "ssh_docker":
                    return await self._handle_docker(arguments)
                elif name == "ssh_generate_key":
                    return await self._handle_generate_key(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        """合并 ssh_config + ssh_login + ssh_connect"""
        host_config = None
        save_config = args.get("save_config", False)

        # Priority 1: user-provided host
        if args.get("host"):
            host_config = SSHHost(
                name="user-server",
                host=args["host"],
                port=args.get("port", 22),
                username=args.get("username", "root"),
                password=args.get("password", ""),
                timeout=args.get("timeout", 30),
                keepalive_interval=args.get("keepalive_interval", 30),
                session_timeout=args.get("session_timeout", 7200)
            )
            self._logger.info(f"Using user-provided host: {args['host']}")

        # Priority 2: hosts.json by name
        if not host_config and args.get("name"):
            host_config = self.config_manager.get_host_by_name(args["name"])
            if not host_config:
                return [TextContent(type="text", text=f"Host '{args['name']}' not found in config/hosts.json")]

        # Priority 3: env vars (fallback)
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
            self._logger.info(f"Using environment variable host: {host_config.host}")

        if not host_config:
            return [TextContent(
                type="text",
                text="No host configured. Provide host/name parameters, or set SSH_HOST env var."
            )]

        if save_config and host_config.password:
            saved = SSHConfig(
                host=host_config.host,
                port=host_config.port,
                username=host_config.username,
                password=host_config.password,
                timeout=host_config.timeout
            )
            self.config_manager.save(saved)

        client_type = self._env_config.get("client_type", "paramiko")

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
            accept_new_host_key=args.get("accept_new_host_key", True),
            private_key_path=Path(args["private_key_path"]) if args.get("private_key_path") else None,
            passphrase=args.get("passphrase"),
        )

        try:
            session_info = await self.session_manager.create_session(config)

            if self._audit:
                self._audit.log_connect(
                    username=config.username, host=config.host, port=config.port,
                    client_type=config.client_type, session_id=session_info.session_id, success=True
                )

            output = (f"Connected to {session_info.host}:{session_info.port}\n"
                      f"Session ID: {session_info.session_id}\n"
                      f"Username: {session_info.username}\n"
                      f"Connected at: {session_info.connected_at.isoformat()}")
            if save_config:
                output += "\nConfig saved for future use."

            command = args.get("command")
            if command:
                session = await self.session_manager.get_session(session_info.session_id)
                result = await session.execute_command(command)
                output += "\n\n--- Command Output ---\n"
                output += f"Exit Code: {result['exit_code']}\n"
                if result["stdout"]:
                    output += f"\n{result['stdout']}"
                if result["stderr"]:
                    output += f"\n--- STDERR ---\n{result['stderr']}"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            self._logger.error(f"Connection failed: {e}")
            if self._audit:
                self._audit.log_connect(
                    username=config.username, host=config.host, port=config.port,
                    client_type=config.client_type, success=False, error_message=str(e)
                )
            return [TextContent(
                type="text",
                text=f"Connection failed: {str(e)}\n\n"
                     f"Check:\n"
                     f"1. Server address and port\n"
                     f"2. Username and password/key\n"
                     f"3. Network connectivity\n"
                     f"4. SSH service is running"
            )]

    async def _handle_execute(self, args: dict) -> list[TextContent]:
        """合并 ssh_execute + ssh_background_task + ssh_fallback_execute + ssh_execute_wait + ssh_task_status"""
        from .security import SecurityError, command_validator, path_validator

        command = args["command"]
        session_id = args.get("session_id")
        timeout = args.get("timeout", 30)
        background = args.get("background", None)

        # Auto-connect if no session_id (fallback mode)
        if not session_id:
            if not self._env_config or not self._env_config.get("host"):
                return [TextContent(type="text", text="No session_id provided and no SSH_HOST env var configured.")]
            connect_result = await self._handle_connect({})
            text = connect_result[0].text
            for line in text.split('\n'):
                if 'Session ID:' in line:
                    session_id = line.split('Session ID:')[1].strip()
                    break
            if not session_id:
                return [TextContent(type="text", text="Auto-connect failed.")]

        # Security validation
        try:
            command_validator.validate_command(command)
        except SecurityError as e:
            self._logger.error(f"Command blocked: {e}")
            return [TextContent(
                type="text",
                text=f"""Command blocked by security policy

Blocked command: `{command}`
Reason: {str(e)}

Solutions:
1. Set SSH_SECURITY_LEVEL=relaxed in MCP env config
2. Add SSH_EXTRA_ALLOWED_COMMANDS with the blocked command

Current security level: {os.getenv('SSH_SECURITY_LEVEL', 'balanced')}"""
            )]

        # Auto-detect background if not specified
        if background is None:
            background = self._should_run_background(command)

        if background:
            return await self._execute_background(session_id, command, args, timeout)

        # Normal execution
        session = await self.session_manager.get_session(session_id)
        if not session:
            return [TextContent(type="text", text=f"Session not found: {session_id}")]

        result = await session.execute_command(command, timeout=timeout)

        if self._audit:
            import time
            session_info = await self.session_manager.get_session(session_id)
            self._audit.log_command(
                username=session_info.username if session_info else "unknown",
                host=session_info.host if session_info else "unknown",
                command=command,
                return_code=result.get('exit_code', -1),
                stdout_length=len(result.get('stdout', '')),
                stderr_length=len(result.get('stderr', '')),
                session_id=session_id,
                execution_time_ms=0
            )

        output = f"Exit Code: {result['exit_code']}\n"
        if result["stdout"]:
            output += f"\n--- STDOUT ---\n{result['stdout']}"
        if result["stderr"]:
            output += f"\n--- STDERR ---\n{result['stderr']}"

        return [TextContent(type="text", text=output)]

    async def _execute_background(self, session_id: str, command: str, args: dict, timeout: int) -> list[TextContent]:
        """Execute a command as a background task"""
        from .security import SecurityError, command_validator, path_validator

        workdir = args.get("workdir", "/tmp")
        log_file = args.get("log_file", "/tmp/background_task.log")
        wait = args.get("wait", False)
        wait_timeout = args.get("wait_timeout", 60)

        try:
            command_validator.validate_command(command.split()[0] if command.split() else "")
        except SecurityError as e:
            return [TextContent(type="text", text=f"Security error: {str(e)}")]

        try:
            safe_workdir = str(path_validator.validate_path(workdir))
        except SecurityError as e:
            return [TextContent(type="text", text=f"Workdir not allowed: {str(e)}")]

        try:
            safe_log_file = str(path_validator.validate_path(log_file))
        except SecurityError as e:
            return [TextContent(type="text", text=f"Log file path not allowed: {str(e)}")]

        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:', 'chmod -R 777 /']
        for pattern in dangerous_patterns:
            if pattern in command:
                return [TextContent(type="text", text=f"Dangerous operation blocked: '{pattern}'")]

        task_id = str(uuid.uuid4())[:8]

        background_command = f"""
cd {safe_workdir} && nohup {command} > {safe_log_file} 2>&1 &
echo $! > /tmp/task_{task_id}.pid
echo "Task started with PID: $(cat /tmp/task_{task_id}.pid)"
echo "Log file: {safe_log_file}"
"""

        try:
            await self.session_manager.execute_command(session_id, background_command, timeout=30, background=True)

            if wait:
                output = await self._wait_for_task_completion(
                    session_id=session_id, task_id=task_id,
                    log_file=safe_log_file, timeout=wait_timeout
                )
            else:
                output = f"""Background Task Started!

Task ID: {task_id}
Command: {command}
Working Directory: {safe_workdir}
Log File: {safe_log_file}

---
To check progress, use:
  ssh_execute(session_id="{session_id}", command="tail -f {safe_log_file}")
To view full log:
  ssh_execute(session_id="{session_id}", command="cat {safe_log_file}")
"""

            return [TextContent(type="text", text=output)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error starting background task: {str(e)}")]

    async def _wait_for_task_completion(self, session_id: str, task_id: str, log_file: str, timeout: int) -> str:
        pid_file = f"/tmp/task_{task_id}.pid"
        elapsed = 0
        interval = 2

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            check_cmd = f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
            result = await self.session_manager.execute_command(session_id, check_cmd, timeout=10)
            status = result.get("stdout", "").strip()

            if status == "COMPLETED" or status == "NOT_FOUND":
                log_cmd = f"if [ -f {log_file} ]; then cat {log_file}; else echo 'No log file found'; fi"
                log_result = await self.session_manager.execute_command(session_id, log_cmd, timeout=10)
                log_content = log_result.get("stdout", "")

                return f"""Task Completed!

Task ID: {task_id}
Execution Time: ~{elapsed} seconds
Log File: {log_file}

---
Command Output:
{log_content}
"""

        return f"""Task Still Running (Timeout)

Task ID: {task_id}
Waited: {elapsed} seconds (timeout: {timeout}s)
Log File: {log_file}

---
Use ssh_execute to check: cat {log_file}
"""

    def _should_run_background(self, command: str) -> bool:
        command_lower = command.lower()

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
        for cmd in docker_instant_commands:
            if cmd in command_lower:
                return False

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
        database_servers = [
            'mongod', 'mysql', 'mysqld', 'postgres', 'postgresql',
            'redis-server', 'elasticsearch', 'kibana',
            'docker-compose up', 'docker run -d',
        ]
        dev_servers = [
            'webpack-dev-server', 'webpack serve',
            'vite', 'vite dev', 'vite preview',
            'ng serve', 'angular serve',
            'next dev', 'nuxt dev',
            'svelte-kit dev',
        ]
        listen_patterns = [
            '--host', '--port', '0.0.0.0', 'localhost:',
            '-p ', '--listen', '--bind',
        ]

        for server_cmd in web_servers + database_servers + dev_servers:
            if server_cmd in command_lower:
                return True
        for pattern in listen_patterns:
            if pattern in command_lower:
                return True
        if any(flag in command for flag in ['--reload', '--debug', '--no-reload']):
            return True
        if 'systemctl start' in command or 'service start' in command:
            return True
        if any(cmd in command_lower for cmd in ['celery', 'rq worker', 'sidekiq', 'resque']):
            return True

        java_patterns = [
            'java -jar', 'java -cp', 'java -class',
            'mvn spring-boot:run', 'mvn jetty:run', 'mvn tomcat:run',
            'gradle bootrun', 'gradle run', 'gradle apprun', 'gradle jettyrun',
            './mvnw spring-boot:run', './gradlew bootrun', './gradlew run',
            'java -server', 'java -x',
        ]
        for pattern in java_patterns:
            if pattern in command_lower:
                return True
        java_servers = ['tomcat', 'jetty', 'jboss', 'wildfly', 'websphere', 'weblogic', 'glassfish', 'payara', 'liberty']
        for server in java_servers:
            if server in command_lower and ('start' in command_lower or 'run' in command_lower):
                return True
        if 'java' in command_lower and any(kw in command_lower for kw in ['start', 'run', 'launch', 'boot', 'server', 'daemon']):
            return True

        go_patterns = ['go run', 'go build && .', 'go install && ']
        for pattern in go_patterns:
            if pattern in command_lower:
                return True
        rust_patterns = ['cargo run', 'cargo watch -x run', 'rustc --run']
        for pattern in rust_patterns:
            if pattern in command_lower:
                return True
        ruby_patterns = ['ruby app.rb', 'ruby server.rb', 'ruby lib/server.rb', 'rails server', 'rails s', 'rake server', 'puma', 'thin start', 'unicorn', 'passenger start', 'rackup', 'shotgun']
        for pattern in ruby_patterns:
            if pattern in command_lower:
                return True
        php_patterns = ['php -S', 'php -s', 'php server', 'php -t', 'laravel serve', 'symfony server:start', 'symfony serve']
        for pattern in php_patterns:
            if pattern in command_lower:
                return True
        dotnet_patterns = ['dotnet run', 'dotnet watch run', 'dotnet webserver', ' kestrel', ' iisexpress']
        for pattern in dotnet_patterns:
            if pattern in command_lower:
                return True
        scala_patterns = ['sbt run', 'sbt ~run', 'scala -howtorun:object']
        for pattern in scala_patterns:
            if pattern in command_lower:
                return True
        elixir_patterns = ['mix phx.server', 'iex -s mix', 'iex --sname', 'iex -S', 'elixir --sname', 'elixir -e']
        for pattern in elixir_patterns:
            if pattern in command_lower:
                return True
        erlang_patterns = ['erl -sname', 'erl -name', 'rebar3 shell']
        for pattern in erlang_patterns:
            if pattern in command_lower:
                return True
        haskell_patterns = ['stack exec', 'cabal run', 'ghci']
        for pattern in haskell_patterns:
            if pattern in command_lower:
                return True
        clojure_patterns = ['lein run', 'lein ring server', 'boot run']
        for pattern in clojure_patterns:
            if pattern in command_lower:
                return True
        r_patterns = ['rserve', 'rserver', 'shiny::runapp', 'shiny run']
        for pattern in r_patterns:
            if pattern in command_lower:
                return True
        other_servers = ['nginx', 'apache', 'httpd', 'caddy', 'haproxy', 'traefik', 'envoy', 'prometheus', 'grafana-server', 'telegraf', 'consul', 'vault', 'nomad']
        for server in other_servers:
            if server in command_lower:
                return True

        return False

    async def _handle_disconnect(self, args: dict) -> list[TextContent]:
        """合并 ssh_disconnect + ssh_list_sessions"""
        session_id = args.get("session_id")

        if session_id:
            await self.session_manager.close_session(session_id)
            return [TextContent(type="text", text=f"Session {session_id} closed")]

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

        return [TextContent(type="text", text=output)]

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

    async def _handle_host(self, args: dict) -> list[TextContent]:
        """合并 ssh_list_hosts + ssh_add_host + ssh_remove_host"""
        action = args.get("action", "list")

        if action == "list":
            return await self._host_list()
        elif action == "add":
            return await self._host_add(args)
        elif action == "remove":
            return await self._host_remove(args)
        else:
            return [TextContent(type="text", text=f"Unknown action: {action}. Use list, add, or remove.")]

    async def _host_list(self) -> list[TextContent]:
        hosts = self.config_manager.list_hosts()
        output = "SSH Server Configurations\n\n"

        if self._env_config and self._env_config.get("host"):
            output += "[Env] MCP config (mcp.json)\n"
            output += f"  Host: {self._env_config.get('host')}:{self._env_config.get('port', 22)}\n"
            output += f"  User: {self._env_config.get('username')}\n"
            output += f"  Password: {'***' if self._env_config.get('password') else 'not set'}\n\n"

        output += "[File] config/hosts.json\n"
        if hosts:
            for i, host in enumerate(hosts, 1):
                output += f"\n  {i}. {host.name}\n"
                output += f"     Host: {host.host}:{host.port}\n"
                output += f"     User: {host.username}\n"
                output += f"     Password: {'***' if host.password else 'not set'}\n"
                output += f"     Timeout: {host.timeout}s\n"
        else:
            output += "  (empty)\n"

        return [TextContent(type="text", text=output)]

    async def _host_add(self, args: dict) -> list[TextContent]:
        name = args.get("name")
        host = args.get("host")
        if not name or not host:
            return [TextContent(type="text", text="Error: name and host are required for add action")]

        new_host = SSHHost(
            name=name, host=host, port=args.get("port", 22),
            username=args.get("username", "root"), password=args.get("password", ""),
            timeout=args.get("timeout", 60), keepalive_interval=30, session_timeout=7200
        )
        self.config_manager.add_host(new_host)

        return [TextContent(
            type="text",
            text=f"SSH server added!\n\nName: {name}\nHost: {host}:{args.get('port', 22)}\nUser: {args.get('username', 'root')}\n\nUse ssh_connect with name='{name}' to connect."
        )]

    async def _host_remove(self, args: dict) -> list[TextContent]:
        name = args.get("name")
        if not name:
            return [TextContent(type="text", text="Error: name is required for remove action")]

        if self.config_manager.remove_host(name):
            return [TextContent(type="text", text=f"SSH server '{name}' removed")]
        return [TextContent(type="text", text=f"Server '{name}' not found")]

    async def _handle_docker(self, args: dict) -> list[TextContent]:
        """合并 ssh_docker_build + ssh_docker_status + ssh_container_logs"""
        import re

        session_id = args.get("session_id")
        action = args.get("action", "ps")

        if not session_id:
            return [TextContent(type="text", text="Error: session_id is required")]

        if action == "ps":
            result = await self.session_manager.execute_command(
                session_id,
                "docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}'",
                timeout=10
            )
            output = "Docker Containers\n\n"
            output += result.get("stdout", "No running containers")
            return [TextContent(type="text", text=output)]

        elif action == "images":
            image_name = args.get("image_name", "")
            image_filter = f"'{image_name}'" if image_name else ""
            cmd = f"docker images {image_filter} --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=10)
            output = "Docker Images\n\n"
            output += result.get("stdout", "No images found")
            return [TextContent(type="text", text=output)]

        elif action == "build":
            image_name = args.get("image_name")
            dockerfile_path = args.get("dockerfile_path", "./Dockerfile")
            context = args.get("context", ".")
            if not image_name:
                return [TextContent(type="text", text="Error: image_name is required for build action")]

            task_id = str(uuid.uuid4())[:8]
            log_file = f"/tmp/docker_build_{task_id}.log"
            build_cmd = f"cd {context} && docker build -t {image_name} -f {dockerfile_path} ."

            background_args = {
                "session_id": session_id,
                "command": build_cmd,
                "workdir": context,
                "log_file": log_file
            }
            return await self._execute_background(session_id, build_cmd, background_args, 30)

        elif action == "logs":
            container_name = args.get("container_name")
            tail = args.get("tail", 100)
            if not container_name:
                return [TextContent(type="text", text="Error: container_name is required for logs action")]
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', container_name):
                return [TextContent(type="text", text=f"Invalid container name: {container_name}")]

            logs_cmd = f"docker logs {container_name} --tail {tail} 2>&1"
            result = await self.session_manager.execute_command(session_id, logs_cmd, timeout=30)

            output = f"Container Logs: {container_name}\nTail: {tail} lines\n\n--- Logs ---\n"
            output += result.get("stdout", "No logs available")
            if result.get("stderr"):
                output += f"\n--- Errors ---\n{result['stderr']}"
            return [TextContent(type="text", text=output)]

        else:
            return [TextContent(type="text", text=f"Unknown action: {action}. Use ps, images, build, or logs.")]

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
                await self.session_manager.close_all_sessions()


async def main():
    server = SSHMCPServer()
    await server.run()


def run_server():
    import sys
    if not sys.stdin.isatty():
        print("Warning: Running in non-interactive mode (stdin is not a TTY)", file=sys.stderr)
        print("MCP server expects to be run as part of an MCP client", file=sys.stderr)
    asyncio.run(main())


if __name__ == "__main__":
    run_server()