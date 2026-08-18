"""Shared utilities used by multiple tool handlers."""

from __future__ import annotations

import re
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
    1. session_id if provided (validated; stale ids fall through to rebuild)
    2. name/host_name from hosts.json
    3. host directly (with optional port/username/password)
    4. env-config fallback (auto-connect)

    Returns session_id on success, None on failure.
    """
    stale_session_id = None
    session_id = args.get("session_id")
    if session_id:
        # 校验 session_id 存活；get_session 内部会对死会话做透明重建（复用同 id）
        try:
            session = await ctx.session_manager.get_session(session_id)
        except Exception:
            session = None
        if session:
            return session_id
        # session_id 已失效（MCP 进程重启 / 重建失败 / entry 被回收）：
        # 不直接采用必失败的 id，而是走 name/host/env 回退链透明重建，
        # 避免 "Session not found" 中断调用方
        stale_session_id = session_id
        ctx.logger.warning(
            f"session_id {session_id} 已失效，尝试通过 name/host/env 配置重建会话"
        )

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

    # 回退链也无法建连：返回原 session_id，让上层报准确的 "Session not found: {id}"
    return stale_session_id


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
