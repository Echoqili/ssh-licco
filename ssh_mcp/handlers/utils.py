"""Shared utilities used by multiple tool handlers."""

from __future__ import annotations

import os
import re
import shlex
from collections.abc import Awaitable, Callable

from mcp.types import TextContent

from .context import HandlerContext


async def ensure_session(
    ctx: HandlerContext,
    args: dict,
    handle_connect: Callable[[HandlerContext, dict], Awaitable[list[TextContent]]],
) -> str | None:
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
        connect_result = await handle_connect(ctx, connect_args)
        text = connect_result[0].text
        for line in text.split("\n"):
            if "Session ID:" in line:
                return line.split("Session ID:")[1].strip()
        return None

    # Use explicit host
    if args.get("host"):
        connect_args = {}
        for key in ("host", "port", "username", "password", "timeout"):
            if key in args:
                connect_args[key] = args[key]
        connect_result = await handle_connect(ctx, connect_args)
        text = connect_result[0].text
        for line in text.split("\n"):
            if "Session ID:" in line:
                return line.split("Session ID:")[1].strip()
        return None

    # Fallback to env config auto-connect
    if ctx.env_config and ctx.env_config.get("host"):
        connect_result = await handle_connect(ctx, {})
        text = connect_result[0].text
        for line in text.split("\n"):
            if "Session ID:" in line:
                return line.split("Session ID:")[1].strip()
        return None

    return None


def normalize_command_for_remote_guard(command: str) -> tuple[str, str | None]:
    """加固点 3：把命令规范为远端 ForceCommand 可安全解析的形式。

    remote_guard 模式下，远端 sshd 的 ForceCommand 脚本会用 `bash -c "$SSH_ORIGINAL_COMMAND"`
    执行。如果原始命令包含 shell 元字符（| ; & $() ` 等），bash -c 解析时会拆分出
    多条命令或子 shell，绕过 ForceCommand 脚本的白名单校验（白名单只看第一个 token）。

    因此本方法在跳板机侧（第一层）就把命令强制规范为「单一命令 + 参数」形式：
      - 禁止管道 |、命令分隔 ;、后台 &、逻辑 && ||、命令替换 $() ``、重定向 > <、子 shell ()
      - 允许普通参数（含路径、引号包裹的字符串参数）
      - 返回 (规范化后的命令, 错误信息)；错误信息非 None 表示被拦截

    这样远端 ForceCommand 解析出的「基础命令」就是真实要执行的那个，无法通过元字符
    注入隐藏的第二条命令。
    """
    if not command or not command.strip():
        return command, "命令为空"

    # 远端 guard 模式下禁止的元字符/构造
    forbidden = ["|", ";", "&", "&&", "||", "$(", ")", "`", ">", "<", "\n", "\r"]
    for token in forbidden:
        if token in command:
            return command, (
                f"命令包含禁止的 shell 元字符 '{token}'。"
                f"远端 guard 模式要求单一 argv，禁止管道/重定向/命令替换/子 shell。"
            )

    # 子 shell 圆括号（前面已拦 ')'，这里再拦开括号 '(' 作为保险）
    if "(" in command:
        return command, "命令包含禁止的子 shell 构造 '('"
    # 命令长度校验
    if len(command) > 4096:
        return command, "命令过长（最大 4096 字符）"

    # 通过 shlex 解析验证命令格式合法（不实际执行）
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return command, f"命令格式无法解析：{e}"
    if not parts:
        return command, "命令解析后为空"

    # 返回原命令（已通过元字符检查），远端 bash -c 会安全解析
    return command, None


def check_approval_gate(command: str, approval_id: str | None) -> str | None:
    """加固点 4：高危操作审批门禁。

    当 SSH_APPROVAL_GATE=true 时，高危命令（CRITICAL/HIGH 风险）必须携带有效
    approval_id（由 ssh_request_approval 工具申请、人工 approve 后获得）才能执行。

    返回 None 表示放行；返回字符串表示拒绝原因（作为 MCP 返回文本）。
    """
    if os.getenv("SSH_APPROVAL_GATE", "false").lower() != "true":
        return None  # 审批门禁未启用

    from ..security import RiskLevel, command_validator

    risk = command_validator.assess_risk_level(command)

    # 仅 CRITICAL / HIGH 风险需要审批；MEDIUM/LOW/SAFE 直接放行
    if risk not in (RiskLevel.CRITICAL, RiskLevel.HIGH):
        return None

    if not approval_id:
        return (
            f"❌ 高危操作审批门禁拦截\n\n"
            f"Command: {command}\n"
            f"Risk: {risk.value}\n\n"
            f"此命令被判定为「{risk.value}」风险，启用了人工审批门禁（SSH_APPROVAL_GATE=true）。\n"
            f"AI 不能直接下发此类高危运维命令，必须先申请审批：\n\n"
            f"  1. 调用 ssh_request_approval 工具，提交 command 与 reason；\n"
            f"  2. 等待人工审批通过，获得 approval_id；\n"
            f"  3. 用 ssh_execute 携带 approval_id 重新执行。\n\n"
            f"高危命令类别：rm -rf、reboot/shutdown、iptables/防火墙修改、mkfs、dd 覆盘等。"
        )

    # 校验 approval_id 有效性
    from ..approval import ApprovalGate

    gate = ApprovalGate.instance()
    ok, reason = gate.verify(approval_id, command)
    if not ok:
        return (
            f"❌ 审批校验失败\n\n"
            f"approval_id: {approval_id}\n"
            f"Reason: {reason}\n\n"
            f"请重新申请审批（ssh_request_approval）或确认 approval_id 是否匹配当前命令。"
        )
    return None


def diagnose_exit_code(exit_code: int, log_tail: str, stderr: str) -> str:
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


def diagnose_startup_failure(stdout: str, stderr: str, workdir: str) -> str:
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


def should_run_background(command: str) -> bool:
    """判断命令是否应作为后台长运行任务执行。"""
    command_lower = command.lower()

    # 瞬时命令（毫秒级完成）——绝不进后台，否则会被误报为 "DEAD/失败"
    instant_patterns = [
        r"\bnginx\s+(-t|--test|-T|-v|-V|-h|--help|-s\s+(reload|stop|quit|reopen))\b",
        r"\bapache2ctl\s+(configtest|status|graceful|stop|fullstatus)\b",
        r"\bhttpd\s+(-t|--test|-v|-V|-h|--help|-k\s+(stop|graceful))\b",
        r"\bsystemctl\s+(status|is-active|is-enabled|show|list-units|list-unit-files|cat|edit)\b",
        r"\bservice\s+\S+\s+status\b",
        r"\bwhich\s+",
        r"\bwhereis\s+",
        r"\bcommand\s+-v\s+",
        r"\bpython\d*\s+(-V|--version)\b",
        r"\bnode\s+(-v|--version)\b",
        r"\bnpm\s+(-v|--version)\b",
        r"\bpip\d*\s+(-V|--version)\b",
        r"\bjava\s+(-version|--version)\b",
        r"\bgit\s+(--version|version)\b",
        r"\bgo\s+version\b",
        r"\brustc\s+--version\b",
        r"\bcargo\s+--version\b",
    ]
    for pattern in instant_patterns:
        if re.search(pattern, command_lower):
            return False

    docker_instant_commands = [
        "docker start ",
        "docker stop ",
        "docker restart ",
        "docker rm ",
        "docker rmi ",
        "docker pause ",
        "docker unpause ",
        "docker kill ",
        "docker commit ",
        "docker export ",
        "docker import ",
        "docker ps",
        "docker images",
        "docker logs",
        "docker inspect",
        "docker stats",
        "docker top",
        "docker port",
        "docker history",
        "docker pull",
        "docker push",
        "docker save",
        "docker load",
        "docker network ls",
        "docker volume ls",
        "docker system",
        "docker exec",
        "docker attach",
        "docker cp",
        "docker build",
        "docker buildx",
        "docker compose build",
        "docker-compose build",
        "docker tag",
        "docker login",
        "docker logout",
    ]
    for cmd in docker_instant_commands:
        if cmd in command_lower:
            return False

    web_servers = [
        "python app.py",
        "python main.py",
        "python manage.py runserver",
        "npm start",
        "npm run serve",
        "npm run dev",
        "yarn start",
        "yarn serve",
        "yarn dev",
        "node app.js",
        "node server.js",
        "node index.js",
        "flask run",
        "django-admin runserver",
        "uvicorn",
        "gunicorn",
        "waitress-serve",
        "php artisan serve",
        "php -S",
        "rails server",
        "rails s",
        "go run",
        "go build && ./",
    ]
    database_servers = [
        "mongod",
        "mysql",
        "mysqld",
        "postgres",
        "postgresql",
        "redis-server",
        "elasticsearch",
        "kibana",
        "docker-compose up",
        "docker run -d",
    ]
    dev_servers = [
        "webpack-dev-server",
        "webpack serve",
        "vite",
        "vite dev",
        "vite preview",
        "ng serve",
        "angular serve",
        "next dev",
        "nuxt dev",
        "svelte-kit dev",
    ]
    listen_patterns = [
        "--host",
        "--port",
        "0.0.0.0",
        "localhost:",
        "-p ",
        "--listen",
        "--bind",
    ]

    for server_cmd in web_servers + database_servers + dev_servers:
        if server_cmd in command_lower:
            return True
    for pattern in listen_patterns:
        if pattern in command_lower:
            return True
    if any(flag in command for flag in ["--reload", "--debug", "--no-reload"]):
        return True
    if "systemctl start" in command or "service start" in command:
        return True
    if any(cmd in command_lower for cmd in ["celery", "rq worker", "sidekiq", "resque"]):
        return True

    java_patterns = [
        "java -jar",
        "java -cp",
        "java -class",
        "mvn spring-boot:run",
        "mvn jetty:run",
        "mvn tomcat:run",
        "gradle bootrun",
        "gradle run",
        "gradle apprun",
        "gradle jettyrun",
        "./mvnw spring-boot:run",
        "./gradlew bootrun",
        "./gradlew run",
        "java -server",
        "java -x",
    ]
    for pattern in java_patterns:
        if pattern in command_lower:
            return True
    java_servers = [
        "tomcat",
        "jetty",
        "jboss",
        "wildfly",
        "websphere",
        "weblogic",
        "glassfish",
        "payara",
        "liberty",
    ]
    for server in java_servers:
        if server in command_lower and ("start" in command_lower or "run" in command_lower):
            return True
    if "java" in command_lower and any(
        kw in command_lower for kw in ["start", "run", "launch", "boot", "server", "daemon"]
    ):
        return True

    go_patterns = ["go run", "go build && .", "go install && "]
    for pattern in go_patterns:
        if pattern in command_lower:
            return True
    rust_patterns = ["cargo run", "cargo watch -x run", "rustc --run"]
    for pattern in rust_patterns:
        if pattern in command_lower:
            return True
    ruby_patterns = [
        "ruby app.rb",
        "ruby server.rb",
        "ruby lib/server.rb",
        "rails server",
        "rails s",
        "rake server",
        "puma",
        "thin start",
        "unicorn",
        "passenger start",
        "rackup",
        "shotgun",
    ]
    for pattern in ruby_patterns:
        if pattern in command_lower:
            return True
    php_patterns = [
        "php -S",
        "php -s",
        "php server",
        "php -t",
        "laravel serve",
        "symfony server:start",
        "symfony serve",
    ]
    for pattern in php_patterns:
        if pattern in command_lower:
            return True
    dotnet_patterns = [
        "dotnet run",
        "dotnet watch run",
        "dotnet webserver",
        " kestrel",
        " iisexpress",
    ]
    for pattern in dotnet_patterns:
        if pattern in command_lower:
            return True
    scala_patterns = ["sbt run", "sbt ~run", "scala -howtorun:object"]
    for pattern in scala_patterns:
        if pattern in command_lower:
            return True
    elixir_patterns = [
        "mix phx.server",
        "iex -s mix",
        "iex --sname",
        "iex -S",
        "elixir --sname",
        "elixir -e",
    ]
    for pattern in elixir_patterns:
        if pattern in command_lower:
            return True
    erlang_patterns = ["erl -sname", "erl -name", "rebar3 shell"]
    for pattern in erlang_patterns:
        if pattern in command_lower:
            return True
    haskell_patterns = ["stack exec", "cabal run", "ghci"]
    for pattern in haskell_patterns:
        if pattern in command_lower:
            return True
    clojure_patterns = ["lein run", "lein ring server", "boot run"]
    for pattern in clojure_patterns:
        if pattern in command_lower:
            return True
    r_patterns = ["rserve", "rserver", "shiny::runapp", "shiny run"]
    for pattern in r_patterns:
        if pattern in command_lower:
            return True
    other_servers = [
        "nginx",
        "apache",
        "httpd",
        "caddy",
        "haproxy",
        "traefik",
        "envoy",
        "prometheus",
        "grafana-server",
        "telegraf",
        "consul",
        "vault",
        "nomad",
    ]
    for server in other_servers:
        if server in command_lower:
            return True

    return False


def shell_quote(s: str) -> str:
    """转义字符串以安全放入 shell 单引号。"""
    return s.replace("'", "'\\''")


def sanitize_remote_path(path: str) -> str:
    """净化远程路径：保留原始 Unix 路径，仅拦截 shell 注入字符。

    远程路径不能用本地 path_validator（它会把 /tmp resolve 成 D:\\tmp）。
    这里只做最小校验：非空、无 shell 元字符、无路径穿越。
    """
    from ..security import SecurityError

    if not path or not path.strip():
        raise SecurityError("远程路径不能为空")
    # 拦截 shell 注入字符（路径本身不需要这些）
    if re.search(r"[;|&$`\n\r]", path):
        raise SecurityError(f"远程路径含非法字符: {path}")
    return path.strip()
