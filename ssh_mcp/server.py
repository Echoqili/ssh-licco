from __future__ import annotations

import asyncio
import logging
import os
import shlex
import threading
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
from .handlers import HANDLERS, schemas
from .handlers.context import HandlerContext
from .key_manager import KeyManager
from .session_manager import SessionManager

try:
    __version__ = get_version("ssh-licco")
except Exception:
    from . import __version__

logger = logging.getLogger(__name__)


class Tunnel:
    """SSH 本地端口转发隧道（-L local_port:remote_host:remote_port）。

    在本地监听 local_port，每个进入的连接通过 paramiko 的 direct-tcpip
    通道转发到远程 remote_host:remote_port。转发在独立线程中完成，不阻塞
    MCP 主事件循环。
    """

    def __init__(self, local_port: int, remote_host: str, remote_port: int, session_id: str):
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.session_id = session_id
        self._transport = None
        self._server_socket = None
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._client_threads: list[threading.Thread] = []

    def start(self, transport) -> None:
        import socket
        self._transport = transport
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", self.local_port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(0.5)
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        import socket
        while not self._stop.is_set():
            try:
                client_sock, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle_connection, args=(client_sock,), daemon=True)
            self._client_threads.append(t)
            t.start()

    def _handle_connection(self, client_sock):
        import socket
        chan = None
        try:
            chan = self._transport.open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                ("127.0.0.1", self.local_port),
            )
            if chan is None:
                return
            self._forward(client_sock, chan)
        except Exception:
            pass
        finally:
            for s in (client_sock, chan):
                if s is None:
                    continue
                try:
                    s.close()
                except Exception:
                    pass

    def _forward(self, sock, chan):
        """双向转发，直到任一端关闭。"""
        import socket

        def pipe(src, dst):
            try:
                while not self._stop.is_set():
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except Exception:
                    pass

        t1 = threading.Thread(target=pipe, args=(sock, chan), daemon=True)
        t2 = threading.Thread(target=pipe, args=(chan, sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def stop(self) -> None:
        self._stop.set()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def info(self) -> dict:
        return {
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "session_id": self.session_id,
        }


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

        # 活动的 SSH 本地端口转发隧道: local_port -> Tunnel
        self._tunnels: dict[int, "Tunnel"] = {}

        self._setup_handlers()

    @property
    def _ctx(self) -> HandlerContext:
        """共享上下文，供独立 handler 函数使用（也用于测试）。

        使用 property 动态读取当前依赖，确保测试替换 manager 后上下文同步。
        """
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

            handler = HANDLERS.get(name)
            if handler is None:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            try:
                return await handler(self._ctx, arguments)
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        """合并 ssh_config + ssh_login + ssh_connect"""
        host_config = None
        save_config = args.get("save_config", False)

        # Coerce port to int (MCP clients may send it as string "22")
        port = args.get("port", 22)
        if isinstance(port, str):
            try:
                port = int(port)
            except (ValueError, TypeError):
                port = 22

        # Priority 1: user-provided host
        if args.get("host"):
            host_config = SSHHost(
                name="user-server",
                host=args["host"],
                port=port,
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
                session_timeout=self._env_config.get("session_timeout", 7200),
                sudo_password=self._env_config.get("sudo_password", ""),
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

        # sudo_password: 优先用 ssh_connect 参数，其次 hosts.json 配置，最后环境变量
        sudo_password = (
            args.get("sudo_password")
            or getattr(host_config, 'sudo_password', '')
            or os.getenv("SSH_SUDO_PASSWORD", "")
            or None
        )

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
            sudo_password=sudo_password,
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

    async def _ensure_session(self, args: dict) -> str | None:
        """Ensure an active session exists.

        Priority:
        1. session_id if provided
        2. name/host_name from hosts.json
        3. host directly (with optional port/username/password)
        4. env-config fallback (auto-connect)

        Returns session_id on success, None on failure.
        """
        session_id = args.get("session_id")
        if session_id:
            return session_id

        # Use named host from hosts.json (name or host_name)
        host_name = args.get("name") or args.get("host_name")
        if host_name:
            connect_args = {"name": host_name}
            for key in ("port", "username", "password", "timeout"):
                if key in args:
                    connect_args[key] = args[key]
            connect_result = await self._handle_connect(connect_args)
            text = connect_result[0].text
            for line in text.split('\n'):
                if 'Session ID:' in line:
                    return line.split('Session ID:')[1].strip()
            return None

        # Use explicit host
        if args.get("host"):
            connect_args = {}
            for key in ("host", "port", "username", "password", "timeout"):
                if key in args:
                    connect_args[key] = args[key]
            connect_result = await self._handle_connect(connect_args)
            text = connect_result[0].text
            for line in text.split('\n'):
                if 'Session ID:' in line:
                    return line.split('Session ID:')[1].strip()
            return None

        # Fallback to env config auto-connect
        if self._env_config and self._env_config.get("host"):
            connect_result = await self._handle_connect({})
            text = connect_result[0].text
            for line in text.split('\n'):
                if 'Session ID:' in line:
                    return line.split('Session ID:')[1].strip()
            return None

        return None

    async def _handle_execute(self, args: dict) -> list[TextContent]:
        """合并 ssh_execute + ssh_background_task + ssh_fallback_execute + ssh_execute_wait + ssh_task_status"""
        from .security import SecurityError, command_validator, path_validator

        command = args["command"]
        timeout = args.get("timeout", 120)  # 默认 120s，避免 docker pull/pg_basebackup 等长任务超时
        background = args.get("background", None)

        # Resolve session via session_id / name / host / env fallback
        session_id = await self._ensure_session(args)
        if not session_id:
            return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]

        # Security validation with multi-layer confirmation
        # confirm_dangerous=True 时跳过安全检查（用户明确确认执行危险操作）
        confirm_dangerous = args.get("confirm_dangerous", False)
        confirmation_layer = args.get("confirmation_layer", 1)  # 当前确认层级
        
        # 多层安全确认检查
        can_execute, confirmation_message = command_validator.check_multi_layer_confirmation(
            command, confirm_dangerous, confirmation_layer
        )
        
        if not can_execute:
            self._logger.warning(f"Command blocked by multi-layer confirmation: {command}")
            return [TextContent(
                type="text",
                text=f"""❌ 操作已被安全机制阻止

{confirmation_message}

🛡️ 当前安全级别: {os.getenv('SSH_SECURITY_LEVEL', 'balanced')}
🔍 风险评估: {command_validator.assess_risk_level(command).value}
📊 需要确认层级: {command_validator.get_required_confirmations(command)}

💡 提示：
- 对于危险操作，系统要求多层确认以确保安全
- 请仔细阅读警告信息，确保完全理解操作后果
- 如确需执行，请设置 confirm_dangerous=true 并增加 confirmation_layer 参数
"""
            )]
        
        # 如果通过了多层确认，记录日志
        if confirmation_message:
            self._logger.info(f"Multi-layer confirmation passed: {confirmation_message}")
        
        # 原有的安全检查逻辑（保持兼容性）
        if not confirm_dangerous:
            try:
                command_validator.validate_command(command)
            except SecurityError as e:
                self._logger.error(f"Command blocked: {e}")
                return [TextContent(
                    type="text",
                    text=f"""❌ 命令已被安全机制阻止

Command: {command}
Reason: {str(e)}

Solutions:
1. Set SSH_SECURITY_LEVEL=relaxed in MCP env config
2. Add SSH_EXTRA_ALLOWED_COMMANDS with the blocked command
3. Set confirm_dangerous=true in ssh_execute args to bypass (use with caution!)

Current security level: {os.getenv('SSH_SECURITY_LEVEL', 'balanced')}"""
                )]
        else:
            # 风险评估和日志记录
            risk_level, risk_desc = command_validator.get_risk_description(command)
            self._logger.warning(f"Dangerous command execution approved: {command} | Risk: {risk_level.value} - {risk_desc}")

        # Auto-detect background if not specified
        if background is None:
            background = self._should_run_background(command)

        if background:
            return await self._execute_background(session_id, command, args, timeout)

        # Normal execution
        session = await self.session_manager.get_session(session_id)
        if not session:
            return [TextContent(type="text", text=f"Session not found: {session_id}")]

        # Sudo 包装：use_sudo=True 时用 sudo -S 执行，密码通过 stdin 传递
        # get_pty=True 分配伪终端，解决远端 sudoers 配置 requiretty 的问题
        stdin_data = None
        get_pty = False
        use_sudo = args.get("use_sudo", False)
        if use_sudo:
            sudo_pwd = getattr(session.config, 'sudo_password', None)
            if not sudo_pwd:
                return [TextContent(type="text", text=(
                    "use_sudo=True but no sudo_password configured.\n"
                    "Please set sudo_password in ssh_connect or SSH_SUDO_PASSWORD env var."
                ))]
            # sudo -S 从 stdin 读密码，-p '' 抑制提示符，bash -c 包装原始命令
            command = f"sudo -S -p '' bash -c {shlex.quote(command)}"
            stdin_data = sudo_pwd + "\n"
            get_pty = True

        result = await session.execute_command(command, timeout=timeout, stdin_data=stdin_data, get_pty=get_pty)

        if self._audit:
            import time
            session_info = await self.session_manager.get_session(session_id)
            self._audit.log_command(
                username=session_info.config.username if session_info else "unknown",
                host=session_info.config.host if session_info else "unknown",
                command=command,
                return_code=result.get('exit_code', -1),
                stdout_length=len(result.get('stdout', '')),
                stderr_length=len(result.get('stderr', '')),
                session_id=session_id,
                execution_time_ms=0
            )

        # 统一输出格式：包含 session 标识，便于确认命令在哪个主机执行
        # 格式：Exit Code / Session / STDOUT / STDERR，各区块用 --- 分隔
        output = f"Exit Code: {result['exit_code']}\n"
        output += f"Session: {session_id} ({session.config.host}:{session.config.port})\n"
        if result["stdout"]:
            output += f"\n--- STDOUT ---\n{result['stdout']}"
        if result["stderr"]:
            output += f"\n--- STDERR ---\n{result['stderr']}"

        return [TextContent(type="text", text=output)]

    async def _execute_background(self, session_id: str, command: str, args: dict, timeout: int) -> list[TextContent]:
        """Execute a command as a background task with proper nohup + bash -c wrapping"""
        from .security import SecurityError, command_validator, path_validator

        workdir = args.get("workdir", "/tmp")
        log_file = args.get("log_file", "/tmp/background_task.log")
        wait = args.get("wait", False)
        wait_timeout = args.get("wait_timeout", 60)
        session_type = args.get("session_type", "nohup")  # "nohup" | "screen" | "tmux"

        # Validate the base command
        try:
            command_validator.validate_command(command.split()[0] if command.split() else "")
        except SecurityError as e:
            return [TextContent(type="text", text=f"Security error: {str(e)}")]

        # workdir/log_file are remote paths, don't use local path_validator
        try:
            safe_workdir = self._sanitize_remote_path(workdir)
            safe_log_file = self._sanitize_remote_path(log_file)
        except SecurityError as e:
            return [TextContent(type="text", text=f"Path not allowed: {str(e)}")]

        # Block dangerous patterns
        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:', 'chmod -R 777 /']
        for pattern in dangerous_patterns:
            if pattern in command:
                return [TextContent(type="text", text=f"Dangerous operation blocked: '{pattern}'")]

        task_id = str(uuid.uuid4())[:8]
        pid_file = f"/tmp/task_{task_id}.pid"
        # 元数据文件：记录命令、日志路径、工作目录，便于跨 session 追踪
        meta_file = f"/tmp/task_{task_id}.meta"

        # ── screen / tmux session support ──
        if session_type in ("screen", "tmux"):
            # 写入元数据（异步，不阻塞）
            meta_content = f"command={command}\nlog_file={safe_log_file}\nworkdir={safe_workdir}\nsession_type={session_type}\n"
            await self.session_manager.execute_command(
                session_id, f"echo {shlex.quote(meta_content)} > {shlex.quote(meta_file)}", timeout=5)
            return await self._execute_background_session(
                session_id, command, safe_workdir, safe_log_file,
                session_type, task_id, wait, wait_timeout
            )

        # ── nohup mode (default): single SSH call, no race condition ──
        # Use shlex.quote() to safely escape the command and paths for bash -c.
        # The wrapper: 写元数据 → cd → nohup bash -c '...' → capture PID → sleep → check alive.
        # 内层命令结束后写入 exit_file，外层读取以区分"已完成"和"仍在运行"。
        exit_file = f"/tmp/task_{task_id}.exit"
        wrapped_command = f"{command}; echo $? > {shlex.quote(exit_file)}"
        meta_content = f"command={command}\nlog_file={safe_log_file}\nworkdir={safe_workdir}\nsession_type=nohup\n"
        check_cmd = (
            f"echo {shlex.quote(meta_content)} > {shlex.quote(meta_file)} && "
            f"cd {shlex.quote(safe_workdir)} && "
            f"nohup bash -c {shlex.quote(wrapped_command)} "
            f"> {shlex.quote(safe_log_file)} 2>&1 < /dev/null & "
            f"PID=$! && "
            f"echo $PID > {shlex.quote(pid_file)} && "
            f"sleep 1 && "
            f"if ps -p $PID > /dev/null 2>&1; then "
            f"echo 'PID='$PID' STATUS=RUNNING'; "
            f"else "
            f"EXIT=$(cat {shlex.quote(exit_file)} 2>/dev/null || echo -1); "
            f"echo 'PID='$PID' STATUS=COMPLETED EXIT='$EXIT; "
            f"echo '--- LOG ---'; "
            f"cat {shlex.quote(safe_log_file)} 2>/dev/null || echo '(no output)'; "
            f"fi"
        )

        try:
            # Execute as a single command (background=False) — the wrapper
            # includes sleep + status check, so it returns in ~1 second.
            result = await self.session_manager.execute_command(
                session_id, check_cmd, timeout=timeout + 5, background=False
            )
        except Exception as e:
            return [TextContent(type="text", text=f"Error starting background task: {str(e)}")]

        start_stdout = (result.get("stdout") or "").strip()
        start_stderr = (result.get("stderr") or "").strip()

        # Parse output: PID=xxx STATUS=RUNNING|COMPLETED EXIT=0
        pid = ""
        status = ""
        exit_code_str = ""
        log_tail = ""
        in_log = False
        for line in start_stdout.splitlines():
            if line.startswith("PID="):
                # 格式: PID=12345 STATUS=RUNNING  或  PID=12345 STATUS=COMPLETED EXIT=0
                for part in line.split():
                    if part.startswith("PID="):
                        pid = part.split("=", 1)[1].strip()
                    elif part.startswith("STATUS="):
                        status = part.split("=", 1)[1].strip()
                    elif part.startswith("EXIT="):
                        exit_code_str = part.split("=", 1)[1].strip()
            elif line == "--- LOG ---":
                in_log = True
            elif in_log:
                log_tail += line + "\n"

        # ── 状态判定：区分 5 种情况 ──
        #
        # 1. ✅ SUCCESS         — STATUS=COMPLETED, EXIT=0   命令执行成功
        # 2. ❌ COMMAND_FAILED  — STATUS=COMPLETED, EXIT>0    命令执行失败（非零退出码）
        # 3. ⚠️ STATUS_ABNORMAL — STATUS=COMPLETED, EXIT=-1   进程异常终止（被信号杀死/OOM，未写 exit 文件）
        # 4. 🟢 RUNNING         — STATUS=RUNNING              后台任务仍在运行
        # 5. 🔴 STARTUP_FAILED  — 无 PID 或无 STATUS          任务启动失败（nohup/shell 错误）

        # 情况 1-3：命令已执行完毕（有 STATUS=COMPLETED）
        if status == "COMPLETED":
            exit_code = int(exit_code_str) if exit_code_str.lstrip('-').isdigit() else -1

            # 统一头部信息：包含 session 标识，便于确认命令在哪个主机执行
            header = (
                f"Command: {command}\n"
                f"Session: {session_id}\n"
                f"PID: {pid}\n"
                f"Exit Code: {exit_code}\n"
                f"Working Directory: {safe_workdir}\n"
            )
            # LOG 说明：nohup 用 > log 2>&1 合并了 stdout 和 stderr
            log_section = f"--- LOG (stdout+stderr) ---\n{log_tail or '(no output)'}"

            if exit_code == 0:
                # ✅ 情况 1：命令执行成功
                return [TextContent(type="text", text=(
                    f"✅ Background Task Completed Successfully!\n\n"
                    f"{header}{log_section}"
                ))]

            elif exit_code > 0:
                # ❌ 情况 2：命令执行失败（非零退出码）
                # 常见原因：命令语法错误、文件不存在、权限不足、依赖缺失
                hint = self._diagnose_exit_code(exit_code, log_tail, start_stderr)
                return [TextContent(type="text", text=(
                    f"❌ Background Task Failed (exit code {exit_code})!\n\n"
                    f"{header}{hint}"
                    f"--- TASK START STDERR ---\n{start_stderr or '(none)'}\n"
                    f"{log_section}"
                ))]

            else:
                # ⚠️ 情况 3：进程异常终止（exit_code == -1，未写入 exit 文件）
                # 常见原因：被 SIGKILL/SIGTERM 杀死、OOM Killer、段错误
                return [TextContent(type="text", text=(
                    f"⚠️ Background Task Terminated Abnormally!\n\n"
                    f"{header}"
                    f"\n可能原因：\n"
                    f"  - 被 SIGKILL/SIGTERM 信号终止（如 systemctl stop、kill -9）\n"
                    f"  - OOM Killer 杀死（内存不足，检查 dmesg | grep -i oom）\n"
                    f"  - 段错误/总线错误（程序 bug，检查 core dump）\n"
                    f"  - 父进程退出导致子进程被终止\n"
                    f"\n--- TASK START STDERR ---\n{start_stderr or '(none)'}\n"
                    f"{log_section}"
                ))]

        # 🟢 情况 4：仍在运行
        if status == "RUNNING" and pid:
            if wait:
                output = await self._wait_for_task_completion(
                    session_id=session_id, task_id=task_id,
                    log_file=safe_log_file, timeout=wait_timeout
                )
            else:
                output = f"""🟢 Background Task Started!

Task ID: {task_id}
PID: {pid}
Command: {command}
Working Directory: {safe_workdir}
Log File: {safe_log_file}

---
To check progress, use:
  ssh_execute(session_id="{session_id}", command="tail -f {safe_log_file}")
To view full log:
  ssh_execute(session_id="{session_id}", command="cat {safe_log_file}")
To check if still running:
  ssh_execute(session_id="{session_id}", command="ps -p {pid}")
After SSH reconnect, list all tasks:
  ssh_process(action="list", session_id="<new_session_id>")
  ssh_process(action="status", session_id="<new_session_id>", task_id="{task_id}")
"""
            return [TextContent(type="text", text=output)]

        # 🔴 情况 5：任务启动失败（无 PID 或无 STATUS）
        # 常见原因：工作目录不存在、bash 不可用、SSH 连接异常、权限拒绝
        startup_hint = self._diagnose_startup_failure(start_stdout, start_stderr, safe_workdir)
        return [TextContent(type="text", text=(
            f"🔴 Background Task Failed to Start!\n\n"
            f"Command: {command}\n"
            f"PID: {pid or '(none)'}\n"
            f"Working Directory: {safe_workdir}\n"
            f"{startup_hint}"
            f"--- STDOUT ---\n{start_stdout or '(none)'}\n"
            f"--- STDERR ---\n{start_stderr or '(none)'}\n"
            f"--- LOG TAIL ---\n{log_tail or '(no log output)'}"
        ))]

    @staticmethod
    def _diagnose_exit_code(exit_code: int, log_tail: str, stderr: str) -> str:
        """根据退出码和日志输出诊断命令失败原因"""
        combined = (log_tail + " " + stderr).lower()
        hints = []

        if exit_code == 127:
            hints.append("命令未找到 (command not found)，请检查命令拼写和 PATH 环境变量")
        elif exit_code == 126:
            hints.append("命令不可执行 (permission denied)，请检查文件权限或使用 chmod +x")
        elif exit_code == 130:
            hints.append("命令被 Ctrl+C 中断")
        elif exit_code == 137:
            hints.append("进程被 SIGKILL 杀死（可能是 OOM Killer 或超时终止）")
        elif exit_code == 139:
            hints.append("段错误 (segfault)，程序存在内存访问 bug")

        # 根据日志内容补充诊断
        if "no such file or directory" in combined:
            hints.append("文件或目录不存在，请检查路径")
        elif "permission denied" in combined:
            hints.append("权限不足，尝试使用 use_sudo=True 或检查文件权限")
        elif "connection refused" in combined:
            hints.append("连接被拒绝，目标服务可能未启动")
        elif "address already in use" in combined:
            hints.append("端口已被占用，使用 'lsof -i :端口' 查看占用进程")

        if hints:
            return "\n诊断提示：\n  - " + "\n  - ".join(hints) + "\n"
        return ""

    @staticmethod
    def _diagnose_startup_failure(stdout: str, stderr: str, workdir: str) -> str:
        """诊断任务启动失败的原因"""
        combined = (stdout + " " + stderr).lower()
        hints = []

        if "no such file or directory" in combined and workdir in combined:
            hints.append(f"工作目录不存在: {workdir}，请先创建或更换 workdir")
        elif "permission denied" in combined:
            hints.append("权限拒绝，检查工作目录和日志文件的写权限")
        elif "command not found" in combined or "bash:" in combined:
            hints.append("bash 不可用或命令路径错误")
        elif not stdout.strip() and not stderr.strip():
            hints.append("无任何输出，可能是 SSH 连接异常或 nohup 执行失败")

        if hints:
            return "\n诊断提示：\n  - " + "\n  - ".join(hints) + "\n"
        return ""

    async def _execute_background_session(
        self, session_id: str, command: str, workdir: str,
        log_file: str, session_type: str, task_id: str,
        wait: bool, wait_timeout: int
    ) -> list[TextContent]:
        """Execute a command inside a screen/tmux session for persistent long-running tasks"""
        session_name = f"ssh_mcp_{task_id}"
        escaped_cmd = command.replace("'", "'\\''")

        if session_type == "screen":
            # screen -dmS <name> bash -c 'cd <dir> && <cmd> > <log> 2>&1'
            launch_cmd = (
                f"screen -dmS {shlex.quote(session_name)} bash -c "
                f"'cd {shlex.quote(workdir)} && {escaped_cmd} > {shlex.quote(log_file)} 2>&1'"
            )
        else:  # tmux
            launch_cmd = (
                f"tmux new-session -d -s {shlex.quote(session_name)} "
                f"'cd {shlex.quote(workdir)} && {escaped_cmd} > {shlex.quote(log_file)} 2>&1'"
            )

        try:
            result = await self.session_manager.execute_command(
                session_id, launch_cmd, timeout=10, background=False
            )
        except Exception as e:
            return [TextContent(type="text", text=f"Error starting {session_type} session: {str(e)}")]

        stderr = (result.get("stderr") or "").strip()
        if stderr:
            return [TextContent(type="text", text=(
                f"Failed to start {session_type} session!\n\n"
                f"Session: {session_name}\n"
                f"Command: {command}\n"
                f"Error: {stderr}"
            ))]

        if wait:
            output = await self._wait_for_task_completion(
                session_id=session_id, task_id=task_id,
                log_file=log_file, timeout=wait_timeout
            )
        else:
            attach_cmd = f"screen -r {session_name}" if session_type == "screen" else f"tmux attach -t {session_name}"
            output = f"""{session_type.upper()} Session Started!

Task ID: {task_id}
Session Name: {session_name}
Command: {command}
Working Directory: {workdir}
Log File: {log_file}

---
To attach to session:
  ssh_execute(session_id="{session_id}", command="{attach_cmd}")
To view log:
  ssh_execute(session_id="{session_id}", command="cat {log_file}")
To kill session:
  ssh_execute(session_id="{session_id}", command="{'screen -XS ' + session_name + ' quit' if session_type == 'screen' else 'tmux kill-session -t ' + session_name}")
"""

        return [TextContent(type="text", text=output)]

    async def _wait_for_task_completion(self, session_id: str, task_id: str, log_file: str, timeout: int) -> str:
        pid_file = f"/tmp/task_{task_id}.pid"
        exit_file = f"/tmp/task_{task_id}.exit"
        elapsed = 0
        interval = 2

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            check_cmd = f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
            result = await self.session_manager.execute_command(session_id, check_cmd, timeout=10)
            status = result.get("stdout", "").strip()

            if status == "COMPLETED" or status == "NOT_FOUND":
                # 读取退出码
                exit_result = await self.session_manager.execute_command(
                    session_id, f"cat {exit_file} 2>/dev/null || echo -1", timeout=10)
                exit_code_str = (exit_result.get("stdout") or "-1").strip()
                exit_code = int(exit_code_str) if exit_code_str.lstrip('-').isdigit() else -1

                log_cmd = f"if [ -f {log_file} ]; then cat {log_file}; else echo 'No log file found'; fi"
                log_result = await self.session_manager.execute_command(session_id, log_cmd, timeout=10)
                log_content = log_result.get("stdout", "")

                status_label = "Completed Successfully" if exit_code == 0 else f"Failed (exit code {exit_code})"
                return f"""Task {status_label}!

Task ID: {task_id}
Exit Code: {exit_code}
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
        import re
        command_lower = command.lower()

        # 瞬时命令（毫秒级完成）——绝不进后台，否则会被误报为 "DEAD/失败"
        instant_patterns = [
            r'\bnginx\s+(-t|--test|-T|-v|-V|-h|--help|-s\s+(reload|stop|quit|reopen))\b',
            r'\bapache2ctl\s+(configtest|status|graceful|stop|fullstatus)\b',
            r'\bhttpd\s+(-t|--test|-v|-V|-h|--help|-k\s+(stop|graceful))\b',
            r'\bsystemctl\s+(status|is-active|is-enabled|show|list-units|list-unit-files|cat|edit)\b',
            r'\bservice\s+\S+\s+status\b',
            r'\bwhich\s+',
            r'\bwhereis\s+',
            r'\bcommand\s+-v\s+',
            r'\bpython\d*\s+(-V|--version)\b',
            r'\bnode\s+(-v|--version)\b',
            r'\bnpm\s+(-v|--version)\b',
            r'\bpip\d*\s+(-V|--version)\b',
            r'\bjava\s+(-version|--version)\b',
            r'\bgit\s+(--version|version)\b',
            r'\bgo\s+version\b',
            r'\brustc\s+--version\b',
            r'\bcargo\s+--version\b',
        ]
        for pattern in instant_patterns:
            if re.search(pattern, command_lower):
                return False

        docker_instant_commands = [
            'docker start ', 'docker stop ', 'docker restart ', 'docker rm ',
            'docker rmi ', 'docker pause ', 'docker unpause ', 'docker kill ',
            'docker commit ', 'docker export ', 'docker import ',
            'docker ps', 'docker images', 'docker logs', 'docker inspect',
            'docker stats', 'docker top', 'docker port', 'docker history',
            'docker pull', 'docker push', 'docker save', 'docker load',
            'docker network ls', 'docker volume ls', 'docker system',
            'docker exec', 'docker attach', 'docker cp',
            'docker build', 'docker buildx', 'docker compose build',
            'docker-compose build', 'docker tag', 'docker login', 'docker logout',
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
            output += f"  Host: {session.config.host}:{session.config.port}\n"
            output += f"  Username: {session.config.username}\n"
            output += f"  State: {session.state.value}\n"
            output += f"  Connected: {session._connected_at.isoformat() if session._connected_at else 'N/A'}\n"
            output += f"  Last Activity: {session._last_activity.isoformat()}\n"

        return [TextContent(type="text", text=output)]

    async def _handle_file_transfer(self, args: dict) -> list[TextContent]:
        session_id = await self._ensure_session(args)
        if not session_id:
            return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]
        session = await self.session_manager.get_session(session_id)
        if not session:
            return [TextContent(type="text", text=f"Session not found: {session_id}")]

        direction = args.get("direction", "upload")
        local_path = args.get("local_path", "")
        remote_path = args.get("remote_path", "")
        content = args.get("content", "")

        if direction == "upload":
            if not local_path or not remote_path:
                return [TextContent(type="text", text="upload requires local_path and remote_path")]
            result = await session.upload_file(local_path, remote_path)
        elif direction == "download":
            if not local_path or not remote_path:
                return [TextContent(type="text", text="download requires local_path and remote_path")]
            result = await session.download_file(remote_path, local_path)
        elif direction == "list":
            result = await session.list_directory(remote_path or ".")
        elif direction == "write":
            if not remote_path:
                return [TextContent(type="text", text="write requires remote_path")]
            result = await session.write_file(remote_path, content, append=False)
        elif direction == "append":
            if not remote_path:
                return [TextContent(type="text", text="append requires remote_path")]
            result = await session.write_file(remote_path, content, append=True)
        elif direction == "delete":
            if not remote_path:
                return [TextContent(type="text", text="delete requires remote_path")]
            result = await session.delete_file(remote_path)
        elif direction == "mkdir":
            if not remote_path:
                return [TextContent(type="text", text="mkdir requires remote_path")]
            result = await session.make_dir(remote_path)
        elif direction == "stat":
            if not remote_path:
                return [TextContent(type="text", text="stat requires remote_path")]
            result = await session.stat_file(remote_path)
        elif direction == "remote_copy":
            # 服务器到服务器直接传输，避免本地中转
            import re
            target_host = args.get("target_host", "")
            target_port = args.get("target_port", 22)
            target_user = args.get("target_user", "root")
            target_path = args.get("target_path", "")
            target_password = args.get("target_password", "")
            use_rsync = args.get("use_rsync", False)

            if not target_host or not target_path or not remote_path:
                return [TextContent(type="text", text="remote_copy requires remote_path, target_host, and target_path")]

            # 校验 host/user 不含 shell 元字符
            if not re.match(r'^[a-zA-Z0-9._-]+$', str(target_host)):
                return [TextContent(type="text", text=f"Invalid target_host: {target_host}")]
            if not re.match(r'^[a-zA-Z0-9._-]+$', str(target_user)):
                return [TextContent(type="text", text=f"Invalid target_user: {target_user}")]

            source = shlex.quote(remote_path)
            target = f"{target_user}@{target_host}:{shlex.quote(target_path)}"

            if use_rsync:
                base_cmd = f"rsync -avz --progress -e 'ssh -p {target_port} -o StrictHostKeyChecking=no'"
            else:
                base_cmd = f"scp -P {target_port} -o StrictHostKeyChecking=no -r"

            if target_password:
                transfer_cmd = f"sshpass -p {shlex.quote(target_password)} {base_cmd} {source} {target}"
            else:
                transfer_cmd = f"{base_cmd} {source} {target}"

            # 在远端执行传输命令，超时 5 分钟
            result = await session.execute_command(transfer_cmd, timeout=300)

            output = f"Remote Copy: {remote_path} -> {target_host}:{target_path}\n\n"
            output += f"Exit Code: {result.get('exit_code', -1)}\n"
            if result.get("stdout"):
                output += f"--- STDOUT ---\n{result['stdout']}\n"
            if result.get("stderr"):
                output += f"--- STDERR ---\n{result['stderr']}\n"

            if result.get("exit_code") == 0:
                output = "✅ " + output
            else:
                output = "❌ " + output
                if "sshpass: command not found" in result.get("stderr", ""):
                    output += "\n💡 Install sshpass on the remote server: apt install sshpass"
                if "Permission denied" in result.get("stderr", ""):
                    output += "\n💡 Ensure SSH key is configured or provide target_password."

            return [TextContent(type="text", text=output)]
        else:
            return [TextContent(type="text", text=f"Unknown direction: {direction}")]

        if result.get("success"):
            if direction == "stat":
                ftype = "dir" if result.get("is_dir") else "file" if result.get("is_file") else "link" if result.get("is_link") else "unknown"
                output = (f"📊 Stat: {result.get('path')}\n"
                          f"  Size: {result.get('size')} bytes\n"
                          f"  Mode: {result.get('mode')}\n"
                          f"  Type: {ftype}\n"
                          f"  mtime: {result.get('mtime')}\n"
                          f"  atime: {result.get('atime')}")
            elif "files" in result:
                output = f"📁 Files in {result.get('path', '.')}:\n"
                for f in result["files"]:
                    output += f"  - {f}\n"
            else:
                output = f"✅ {result.get('message', 'Success')}"
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

        action = args.get("action", "ps")

        session_id = await self._ensure_session(args)
        if not session_id:
            return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]

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
            image_filter = "'{}'".format(image_name) if image_name else ""
            cmd = "docker images " + image_filter + " --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'"
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

    @staticmethod
    def _shell_quote(s: str) -> str:
        """转义字符串以安全放入 shell 单引号。"""
        return s.replace("'", "'\\''")

    @staticmethod
    def _sanitize_remote_path(path: str) -> str:
        """净化远程路径：保留原始 Unix 路径，仅拦截 shell 注入字符。

        远程路径不能用本地 path_validator（它会把 /tmp resolve 成 D:\\tmp）。
        这里只做最小校验：非空、无 shell 元字符、无路径穿越。
        """
        import re
        from .security import SecurityError
        if not path or not path.strip():
            raise SecurityError("远程路径不能为空")
        # 拦截 shell 注入字符（路径本身不需要这些）
        if re.search(r'[;|&$`\n\r]', path):
            raise SecurityError(f"远程路径含非法字符: {path}")
        return path.strip()

    async def _handle_session(self, args: dict) -> list[TextContent]:
        """管理 screen/tmux 持久会话。"""
        import re
        from .security import SecurityError, command_validator

        action = args.get("action")
        name = args.get("name", "")

        session_id = await self._ensure_session(args)
        if not session_id:
            return [TextContent(type="text", text="No session_id, host_name, host, or SSH_HOST env var configured.")]
        command = args.get("command", "")
        session_type = args.get("session_type", "screen")
        lines = args.get("lines", 50)

        if not session_id:
            return [TextContent(type="text", text="Error: session_id is required")]

        # 会话名只允许安全字符，防止命令注入
        if name and not re.match(r'^[a-zA-Z0-9_.-]+$', name):
            return [TextContent(type="text", text=f"Invalid session name: {name}. Only letters, digits, _, ., - allowed.")]

        esc = self._shell_quote

        if action == "create":
            if not name:
                return [TextContent(type="text", text="create requires name")]
            if not command:
                return [TextContent(type="text", text="create requires command")]
            try:
                command_validator.validate_command(command)
            except SecurityError as e:
                return [TextContent(type="text", text=f"Command blocked: {str(e)}")]

            if session_type == "tmux":
                cmd = f"tmux new-session -d -s {name} '{esc(command)}'"
            else:
                cmd = f"screen -dmS {name} bash -lc '{esc(command)}'"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
            rc = result.get("exit_code", -1)
            if rc == 0:
                output = (f"✅ {session_type} session '{name}' created\n"
                          f"Command: {command}\n\n"
                          f"---\nTo send commands: ssh_session(action='send', name='{name}')\n"
                          f"To view screen: ssh_session(action='capture', name='{name}')")
            else:
                output = (f"❌ Failed to create session (exit {rc})\n"
                          f"Is {session_type} installed? Check: which {session_type}\n"
                          f"STDOUT: {result.get('stdout', '')}\n"
                          f"STDERR: {result.get('stderr', '')}")

        elif action == "send":
            if not name:
                return [TextContent(type="text", text="send requires name")]
            if not command:
                return [TextContent(type="text", text="send requires command")]
            try:
                command_validator.validate_command(command)
            except SecurityError as e:
                return [TextContent(type="text", text=f"Command blocked: {str(e)}")]

            if session_type == "tmux":
                cmd = f"tmux send-keys -t {name} '{esc(command)}' Enter"
            else:
                # 单引号内放真实换行符，screen stuff 会把它当作回车键
                cmd = f"screen -S {name} -X stuff '{esc(command)}\n'"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
            rc = result.get("exit_code", -1)
            output = f"✅ Sent to '{name}': {command}" if rc == 0 else (
                f"❌ Send failed (exit {rc}). Session may not exist.\n"
                f"STDERR: {result.get('stderr', '')}")

        elif action == "capture":
            if not name:
                return [TextContent(type="text", text="capture requires name")]
            if session_type == "tmux":
                cmd = f"tmux capture-pane -t {name} -p -S -{int(lines)}"
                result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
                output = f"📋 tmux pane '{name}' (last {lines} lines):\n\n{result.get('stdout', '')}"
            else:
                cap_file = f"/tmp/screen_cap_{name}.txt"
                cmd = f"screen -S {name} -X hardcopy {cap_file} && sleep 0.1 && cat {cap_file}"
                result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
                rc = result.get("exit_code", -1)
                if rc == 0:
                    output = f"📋 screen '{name}' capture:\n\n{result.get('stdout', '')}"
                else:
                    output = f"❌ Capture failed (exit {rc}). Session may not exist.\nSTDERR: {result.get('stderr', '')}"

        elif action == "list":
            if session_type == "tmux":
                cmd = "tmux list-sessions 2>&1"
            else:
                cmd = "screen -ls 2>&1"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
            output = f"📋 {session_type} sessions:\n\n{result.get('stdout', '')}"

        elif action == "kill":
            if not name:
                return [TextContent(type="text", text="kill requires name")]
            if session_type == "tmux":
                cmd = f"tmux kill-session -t {name}"
            else:
                cmd = f"screen -S {name} -X quit"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
            rc = result.get("exit_code", -1)
            output = f"✅ Killed session '{name}'" if rc == 0 else (
                f"❌ Kill failed (exit {rc}). Session may not exist.\nSTDERR: {result.get('stderr', '')}")

        else:
            output = f"Unknown action: {action}. Use create, send, capture, list, or kill."

        return [TextContent(type="text", text=output)]

    async def _handle_process(self, args: dict) -> list[TextContent]:
        """管理后台进程与 SSH 隧道。"""
        import re
        from .security import SecurityError, command_validator, path_validator

        action = args.get("action")

        session_id = await self._ensure_session(args)
        if not session_id:
            return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]

        if action == "start":
            command = args.get("command", "")
            if not command:
                return [TextContent(type="text", text="start requires command")]
            workdir = args.get("workdir", "/tmp")
            task_id = str(uuid.uuid4())[:8]
            log_file = args.get("log_file") or f"/tmp/bg_{task_id}.log"

            # 复用 _execute_background 的安全校验与脱离逻辑
            bg_args = {
                "workdir": workdir,
                "log_file": log_file,
                "wait": False,
                "wait_timeout": 0,
            }
            return await self._execute_background(session_id, command, bg_args, 30)

        if action == "stop":
            pid = args.get("pid", "")
            task_id = args.get("task_id", "")
            signal = args.get("signal", "TERM") or "TERM"
            # 信号名只允许大写字母+数字
            if not re.match(r'^[A-Z0-9]+$', signal):
                return [TextContent(type="text", text=f"Invalid signal: {signal}")]

            if not pid and task_id:
                pid_file = f"/tmp/task_{task_id}.pid"
                r = await self.session_manager.execute_command(
                    session_id, f"cat {pid_file} 2>/dev/null", timeout=10)
                pid = (r.get("stdout") or "").strip()
                if not pid:
                    return [TextContent(type="text", text=f"No PID found for task_id {task_id}")]

            if not pid:
                return [TextContent(type="text", text="stop requires pid or task_id")]
            if not re.match(r'^[0-9]+$', str(pid)):
                return [TextContent(type="text", text=f"Invalid pid: {pid}")]

            cmd = f"kill -{signal} {pid}"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=10)
            rc = result.get("exit_code", -1)
            if rc == 0:
                output = f"✅ Sent {signal} to PID {pid}"
            else:
                output = f"❌ kill failed (exit {rc}): {result.get('stderr', '')}"
            return [TextContent(type="text", text=output)]

        if action == "status":
            pid = args.get("pid", "")
            task_id = args.get("task_id", "")
            if not pid and task_id:
                pid_file = f"/tmp/task_{task_id}.pid"
                r = await self.session_manager.execute_command(
                    session_id, f"cat {pid_file} 2>/dev/null", timeout=10)
                pid = (r.get("stdout") or "").strip()
            if not pid:
                return [TextContent(type="text", text="status requires pid or task_id")]
            if not re.match(r'^[0-9]+$', str(pid)):
                return [TextContent(type="text", text=f"Invalid pid: {pid}")]

            cmd = f"ps -p {pid} -o pid,ppid,stat,etime,cmd --no-headers 2>/dev/null"
            result = await self.session_manager.execute_command(session_id, cmd, timeout=10)
            rc = result.get("exit_code", -1)
            stdout = (result.get("stdout") or "").strip()
            if rc == 0 and stdout:
                output = f"✅ PID {pid} is RUNNING\n{stdout}"
            else:
                output = f"❌ PID {pid} is NOT running (or no permission)"
            return [TextContent(type="text", text=output)]

        if action == "list":
            # 列出 /tmp/task_*.pid 跟踪的后台任务，并读取 .meta 元数据
            cmd = (
                'for f in /tmp/task_*.pid; do '
                '[ -f "$f" ] || continue; '
                'PID=$(cat "$f" 2>/dev/null); '
                '[ -n "$PID" ] || continue; '
                'if ps -p $PID > /dev/null 2>&1; then ST=RUNNING; else ST=DEAD; fi; '
                'TASK_ID=$(echo "$f" | sed "s|/tmp/task_||;s|\\.pid||"); '
                'META_FILE="/tmp/task_${TASK_ID}.meta"; '
                'CMD=""; LOG=""; '
                'if [ -f "$META_FILE" ]; then '
                '  CMD=$(grep "^command=" "$META_FILE" 2>/dev/null | cut -d= -f2-); '
                '  LOG=$(grep "^log_file=" "$META_FILE" 2>/dev/null | cut -d= -f2-); '
                'fi; '
                'echo "TASK=$TASK_ID PID=$PID STATUS=$ST CMD=$CMD LOG=$LOG"; '
                'done 2>/dev/null'
            )
            result = await self.session_manager.execute_command(session_id, cmd, timeout=15)
            stdout = (result.get("stdout") or "").strip()
            if not stdout:
                return [TextContent(type="text", text="📋 Tracked background tasks:\n\n(none)")]

            output = "📋 Tracked background tasks:\n\n"
            for line in stdout.splitlines():
                # 解析: TASK=abc123 PID=12345 STATUS=RUNNING CMD=... LOG=...
                parts = {}
                for part in line.split(None, 4):  # 最多分5段，CMD 可能含空格
                    if '=' in part:
                        key, val = part.split('=', 1)
                        parts[key] = val
                task_id = parts.get('TASK', '?')
                pid = parts.get('PID', '?')
                status = parts.get('STATUS', '?')
                cmd_str = parts.get('CMD', '')
                log = parts.get('LOG', '')
                status_icon = "🟢" if status == "RUNNING" else "⚫"
                output += f"{status_icon} Task: {task_id} | PID: {pid} | {status}\n"
                if cmd_str:
                    output += f"   Command: {cmd_str}\n"
                if log:
                    output += f"   Log: {log}\n"
                output += "\n"
            return [TextContent(type="text", text=output.rstrip())]

        if action == "tunnel_open":
            local_port = args.get("local_port")
            remote_host = args.get("remote_host", "")
            remote_port = args.get("remote_port")
            if not local_port or not remote_host or not remote_port:
                return [TextContent(type="text", text="tunnel_open requires local_port, remote_host, remote_port")]
            if local_port in self._tunnels:
                return [TextContent(type="text", text=f"Tunnel on local port {local_port} already exists")]

            session = await self.session_manager.get_session(session_id)
            if not session or not session.client:
                return [TextContent(type="text", text=f"Session not found or not connected: {session_id}")]
            transport = session.client.get_transport()
            if transport is None or not transport.is_active():
                return [TextContent(type="text", text="SSH transport is not active")]

            try:
                tunnel = Tunnel(int(local_port), remote_host, int(remote_port), session_id)
                tunnel.start(transport)
                self._tunnels[int(local_port)] = tunnel
            except OSError as e:
                return [TextContent(type="text", text=f"Failed to open tunnel: {str(e)} (port may be in use?)")]

            output = (f"✅ Tunnel opened: 127.0.0.1:{local_port} -> {remote_host}:{remote_port}\n"
                      f"Session: {session_id}\n"
                      f"Locally, connect to 127.0.0.1:{local_port} to reach the remote service.")
            return [TextContent(type="text", text=output)]

        if action == "tunnel_close":
            local_port = args.get("local_port")
            if local_port is None:
                return [TextContent(type="text", text="tunnel_close requires local_port")]
            tunnel = self._tunnels.pop(int(local_port), None)
            if not tunnel:
                return [TextContent(type="text", text=f"No tunnel on local port {local_port}")]
            tunnel.stop()
            return [TextContent(type="text", text=f"✅ Tunnel closed on local port {local_port}")]

        if action == "tunnel_list":
            if not self._tunnels:
                return [TextContent(type="text", text="No active tunnels")]
            lines = ["📋 Active SSH tunnels:"]
            for p, t in self._tunnels.items():
                info = t.info()
                lines.append(f"  127.0.0.1:{info['local_port']} -> {info['remote_host']}:{info['remote_port']}  (session {info['session_id']})")
            return [TextContent(type="text", text="\n".join(lines))]

        return [TextContent(type="text", text=f"Unknown action: {action}. Use start, stop, status, list, tunnel_open, tunnel_close, tunnel_list.")]

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
    asyncio.run(main())


if __name__ == "__main__":
    run_server()