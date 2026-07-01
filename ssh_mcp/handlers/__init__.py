"""ssh_mcp tool handlers package."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from mcp.types import TextContent

from . import schemas
from .approval import handle_approve_command, handle_list_approvals, handle_request_approval
from .connect import handle_connect, handle_disconnect
from .context import HandlerContext
from .docker import handle_docker
from .execute import handle_execute
from .file_transfer import handle_file_transfer
from .host import handle_host
from .key import handle_generate_key
from .process import handle_process
from .session import handle_session

Handler = Callable[[HandlerContext, dict], Awaitable[list[TextContent]]]

HANDLERS: dict[str, Handler] = {
    "ssh_connect": handle_connect,
    "ssh_execute": handle_execute,
    "ssh_disconnect": handle_disconnect,
    "ssh_file_transfer": handle_file_transfer,
    "ssh_host": handle_host,
    "ssh_docker": handle_docker,
    "ssh_generate_key": handle_generate_key,
    "ssh_session": handle_session,
    "ssh_process": handle_process,
    "ssh_request_approval": handle_request_approval,
    "ssh_approve_command": handle_approve_command,
    "ssh_list_approvals": handle_list_approvals,
}

__all__ = ["HANDLERS", "schemas"]
