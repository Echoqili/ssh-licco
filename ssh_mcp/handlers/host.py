"""Handler for ssh_host management."""

from __future__ import annotations

from mcp.types import TextContent

from ..config_manager import SSHHost
from .context import HandlerContext


async def handle_host(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Manage SSH server configurations in hosts.json."""
    action = args.get("action", "list")

    if action == "list":
        return await _host_list(ctx)
    elif action == "add":
        return await _host_add(ctx, args)
    elif action == "remove":
        return await _host_remove(ctx, args)
    else:
        return [TextContent(type="text", text=f"Unknown action: {action}. Use list, add, or remove.")]


async def _host_list(ctx: HandlerContext) -> list[TextContent]:
    hosts = ctx.config_manager.list_hosts()
    output = "SSH Server Configurations\n\n"

    if ctx.env_config and ctx.env_config.get("host"):
        output += "[Env] MCP config (mcp.json)\n"
        output += f"  Host: {ctx.env_config.get('host')}:{ctx.env_config.get('port', 22)}\n"
        output += f"  User: {ctx.env_config.get('username')}\n"
        output += f"  Password: {'***' if ctx.env_config.get('password') else 'not set'}\n\n"

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


async def _host_add(ctx: HandlerContext, args: dict) -> list[TextContent]:
    name = args.get("name")
    host = args.get("host")
    if not name or not host:
        return [TextContent(type="text", text="Error: name and host are required for add action")]

    new_host = SSHHost(
        name=name, host=host, port=args.get("port", 22),
        username=args.get("username", "root"), password=args.get("password", ""),
        timeout=args.get("timeout", 60), keepalive_interval=30, session_timeout=7200
    )
    ctx.config_manager.add_host(new_host)

    return [TextContent(
        type="text",
        text=f"SSH server added!\n\nName: {name}\nHost: {host}:{args.get('port', 22)}\nUser: {args.get('username', 'root')}\n\nUse ssh_connect with name='{name}' to connect."
    )]


async def _host_remove(ctx: HandlerContext, args: dict) -> list[TextContent]:
    name = args.get("name")
    if not name:
        return [TextContent(type="text", text="Error: name is required for remove action")]

    if ctx.config_manager.remove_host(name):
        return [TextContent(type="text", text=f"SSH server '{name}' removed")]
    return [TextContent(type="text", text=f"Server '{name}' not found")]
