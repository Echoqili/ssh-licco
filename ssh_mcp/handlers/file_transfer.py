"""Handler for ssh_file_transfer."""

from __future__ import annotations

import re
import shlex

from mcp.types import TextContent

from .connect import handle_connect
from .context import HandlerContext
from .utils import ensure_session


async def handle_file_transfer(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Transfer files between local and remote, or perform remote file operations."""
    session_id = await ensure_session(ctx, args, handle_connect)
    if not session_id:
        return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]
    session = await ctx.session_manager.get_session(session_id)
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
