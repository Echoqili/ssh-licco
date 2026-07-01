"""Handler for ssh_process and SSH tunnels."""

from __future__ import annotations

import re
import uuid

from mcp.types import TextContent

from ..tunnel import Tunnel
from .connect import handle_connect
from .context import HandlerContext
from .execute import execute_background
from .utils import ensure_session


async def handle_process(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Manage background processes and SSH tunnels."""
    action = args.get("action")

    session_id = await ensure_session(ctx, args, handle_connect)
    if not session_id:
        return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]

    if action == "start":
        command = args.get("command", "")
        if not command:
            return [TextContent(type="text", text="start requires command")]
        workdir = args.get("workdir", "/tmp")
        task_id = str(uuid.uuid4())[:8]
        log_file = args.get("log_file") or f"/tmp/bg_{task_id}.log"

        # 复用 execute_background 的安全校验与脱离逻辑
        bg_args = {
            "workdir": workdir,
            "log_file": log_file,
            "wait": False,
            "wait_timeout": 0,
        }
        return await execute_background(ctx, session_id, command, bg_args, 30)

    if action == "stop":
        pid = args.get("pid", "")
        task_id = args.get("task_id", "")
        signal = args.get("signal", "TERM") or "TERM"
        # 信号名只允许大写字母+数字
        if not re.match(r'^[A-Z0-9]+$', signal):
            return [TextContent(type="text", text=f"Invalid signal: {signal}")]

        if not pid and task_id:
            pid_file = f"/tmp/task_{task_id}.pid"
            r = await ctx.session_manager.execute_command(
                session_id, f"cat {pid_file} 2>/dev/null", timeout=10)
            pid = (r.get("stdout") or "").strip()
            if not pid:
                return [TextContent(type="text", text=f"No PID found for task_id {task_id}")]

        if not pid:
            return [TextContent(type="text", text="stop requires pid or task_id")]
        if not re.match(r'^[0-9]+$', str(pid)):
            return [TextContent(type="text", text=f"Invalid pid: {pid}")]

        cmd = f"kill -{signal} {pid}"
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=10)
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
            r = await ctx.session_manager.execute_command(
                session_id, f"cat {pid_file} 2>/dev/null", timeout=10)
            pid = (r.get("stdout") or "").strip()
        if not pid:
            return [TextContent(type="text", text="status requires pid or task_id")]
        if not re.match(r'^[0-9]+$', str(pid)):
            return [TextContent(type="text", text=f"Invalid pid: {pid}")]

        cmd = f"ps -p {pid} -o pid,ppid,stat,etime,cmd --no-headers 2>/dev/null"
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=10)
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
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
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
        if local_port in ctx.tunnels:
            return [TextContent(type="text", text=f"Tunnel on local port {local_port} already exists")]

        session = await ctx.session_manager.get_session(session_id)
        if not session or not session.client:
            return [TextContent(type="text", text=f"Session not found or not connected: {session_id}")]
        transport = session.client.get_transport()
        if transport is None or not transport.is_active():
            return [TextContent(type="text", text="SSH transport is not active")]

        try:
            tunnel = Tunnel(int(local_port), remote_host, int(remote_port), session_id)
            tunnel.start(transport)
            ctx.tunnels[int(local_port)] = tunnel
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
        tunnel = ctx.tunnels.pop(int(local_port), None)
        if not tunnel:
            return [TextContent(type="text", text=f"No tunnel on local port {local_port}")]
        tunnel.stop()
        return [TextContent(type="text", text=f"✅ Tunnel closed on local port {local_port}")]

    if action == "tunnel_list":
        if not ctx.tunnels:
            return [TextContent(type="text", text="No active tunnels")]
        lines = ["📋 Active SSH tunnels:"]
        for _port, t in ctx.tunnels.items():
            info = t.info()
            lines.append(f"  127.0.0.1:{info['local_port']} -> {info['remote_host']}:{info['remote_port']}  (session {info['session_id']})")
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown action: {action}. Use start, stop, status, list, tunnel_open, tunnel_close, tunnel_list.")]
