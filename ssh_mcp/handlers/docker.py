"""Handler for ssh_docker."""

from __future__ import annotations

import re
import uuid

from mcp.types import TextContent

from .connect import handle_connect
from .context import HandlerContext
from .execute import execute_background
from .utils import ensure_session


async def handle_docker(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Merge ssh_docker_build + ssh_docker_status + ssh_container_logs."""
    action = args.get("action", "ps")

    session_id = await ensure_session(ctx, args, handle_connect)
    if not session_id:
        return [TextContent(type="text", text="No session_id, name, host, or SSH_HOST env var configured.")]

    if action == "ps":
        result = await ctx.session_manager.execute_command(
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
        result = await ctx.session_manager.execute_command(session_id, cmd, timeout=10)
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
        return await execute_background(ctx, session_id, build_cmd, background_args, 30)

    elif action == "logs":
        container_name = args.get("container_name")
        tail = args.get("tail", 100)
        if not container_name:
            return [TextContent(type="text", text="Error: container_name is required for logs action")]
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', container_name):
            return [TextContent(type="text", text=f"Invalid container name: {container_name}")]

        logs_cmd = f"docker logs {container_name} --tail {tail} 2>&1"
        result = await ctx.session_manager.execute_command(session_id, logs_cmd, timeout=30)

        output = f"Container Logs: {container_name}\nTail: {tail} lines\n\n--- Logs ---\n"
        output += result.get("stdout", "No logs available")
        if result.get("stderr"):
            output += f"\n--- Errors ---\n{result['stderr']}"
        return [TextContent(type="text", text=output)]

    else:
        return [TextContent(type="text", text=f"Unknown action: {action}. Use ps, images, build, or logs.")]
