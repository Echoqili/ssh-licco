"""Handler for ssh_session (screen/tmux)."""

from __future__ import annotations

import re

from mcp.types import TextContent

from ..security import SecurityError, command_validator
from .connect import handle_connect
from .context import HandlerContext
from .utils import ensure_session, shell_quote


async def handle_session(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Manage screen/tmux persistent sessions."""
    action = args.get("action")
    name = args.get("name", "")

    session_id = await ensure_session(ctx, args, handle_connect)
    if not session_id:
        return [
            TextContent(
                type="text", text="No session_id, host_name, host, or SSH_HOST env var configured."
            )
        ]
    command = args.get("command", "")
    session_type = args.get("session_type", "screen")
    lines = args.get("lines", 50)

    if not session_id:
        return [TextContent(type="text", text="Error: session_id is required")]

    # 会话名只允许安全字符，防止命令注入
    if name and not re.match(r"^[a-zA-Z0-9_.-]+$", name):
        return [
            TextContent(
                type="text",
                text=f"Invalid session name: {name}. Only letters, digits, _, ., - allowed.",
            )
        ]

    esc = shell_quote

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
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
        rc = result.get("exit_code", -1)
        if rc == 0:
            output = (
                f"✅ {session_type} session '{name}' created\n"
                f"Command: {command}\n\n"
                f"---\nTo send commands: ssh_session(action='send', name='{name}')\n"
                f"To view screen: ssh_session(action='capture', name='{name}')"
            )
        else:
            output = (
                f"❌ Failed to create session (exit {rc})\n"
                f"Is {session_type} installed? Check: which {session_type}\n"
                f"STDOUT: {result.get('stdout', '')}\n"
                f"STDERR: {result.get('stderr', '')}"
            )

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
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
        rc = result.get("exit_code", -1)
        output = (
            f"✅ Sent to '{name}': {command}"
            if rc == 0
            else (
                f"❌ Send failed (exit {rc}). Session may not exist.\n"
                f"STDERR: {result.get('stderr', '')}"
            )
        )

    elif action == "capture":
        if not name:
            return [TextContent(type="text", text="capture requires name")]
        if session_type == "tmux":
            cmd = f"tmux capture-pane -t {name} -p -S -{int(lines)}"
            result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
            output = f"📋 tmux pane '{name}' (last {lines} lines):\n\n{result.get('stdout', '')}"
        else:
            cap_file = f"/tmp/screen_cap_{name}.txt"
            cmd = f"screen -S {name} -X hardcopy {cap_file} && sleep 0.1 && cat {cap_file}"
            result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
            rc = result.get("exit_code", -1)
            if rc == 0:
                output = f"📋 screen '{name}' capture:\n\n{result.get('stdout', '')}"
            else:
                output = (
                    f"❌ Capture failed (exit {rc}). "
                    f"Session may not exist.\nSTDERR: {result.get('stderr', '')}"
                )

    elif action == "list":
        if session_type == "tmux":
            cmd = "tmux list-sessions 2>&1"
        else:
            cmd = "screen -ls 2>&1"
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
        output = f"📋 {session_type} sessions:\n\n{result.get('stdout', '')}"

    elif action == "kill":
        if not name:
            return [TextContent(type="text", text="kill requires name")]
        if session_type == "tmux":
            cmd = f"tmux kill-session -t {name}"
        else:
            cmd = f"screen -S {name} -X quit"
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=15)
        rc = result.get("exit_code", -1)
        output = (
            f"✅ Killed session '{name}'"
            if rc == 0
            else (
                f"❌ Kill failed (exit {rc}). "
                f"Session may not exist.\nSTDERR: {result.get('stderr', '')}"
            )
        )

    else:
        output = f"Unknown action: {action}. Use create, send, capture, list, or kill."

    return [TextContent(type="text", text=output)]
