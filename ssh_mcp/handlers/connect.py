"""Handler for ssh_connect and ssh_disconnect."""

from __future__ import annotations

import os
from pathlib import Path

from mcp.types import TextContent

from ..config_manager import SSHConfig, SSHHost
from ..connection_config import ConnectionConfig
from ..secret_provider import SecretManager, SecretProviderError
from ..security import SecurityError, command_validator
from .context import HandlerContext


async def handle_connect(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Merge ssh_config + ssh_login + ssh_connect."""
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
            session_timeout=args.get("session_timeout", 7200),
        )
        ctx.logger.info(f"Using user-provided host: {args['host']}")

    # Priority 2: hosts.json by name
    if not host_config and args.get("name"):
        host_config = ctx.config_manager.get_host_by_name(args["name"])
        if not host_config:
            return [
                TextContent(
                    type="text", text=f"Host '{args['name']}' not found in config/hosts.json"
                )
            ]

    # Priority 3: env vars (fallback)
    if not host_config and ctx.env_config and ctx.env_config.get("host"):
        host_config = SSHHost(
            name="env-server",
            host=ctx.env_config.get("host", "127.0.0.1"),
            port=ctx.env_config.get("port", 22),
            username=ctx.env_config.get("username", "root"),
            password=ctx.env_config.get("password", ""),
            timeout=ctx.env_config.get("timeout", 30),
            keepalive_interval=ctx.env_config.get("keepalive_interval", 30),
            session_timeout=ctx.env_config.get("session_timeout", 7200),
            sudo_password=ctx.env_config.get("sudo_password", ""),
        )
        ctx.logger.info(f"Using environment variable host: {host_config.host}")

    if not host_config:
        return [
            TextContent(
                type="text",
                text="No host configured. Provide host/name parameters, or set SSH_HOST env var.",
            )
        ]

    if save_config and host_config.password:
        saved = SSHConfig(
            host=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password,
            timeout=host_config.timeout,
        )
        ctx.config_manager.save(saved)

    client_type = ctx.env_config.get("client_type", "paramiko")

    # sudo_password: 优先用 ssh_connect 参数，其次 hosts.json 配置，最后环境变量
    sudo_password = (
        args.get("sudo_password")
        or getattr(host_config, "sudo_password", "")
        or os.getenv("SSH_SUDO_PASSWORD", "")
        or None
    )

    # 加固点 2：密钥不落地磁盘
    # 当 SecretManager 启用时，自动从 KMS 临时拉取私钥到内存，不读磁盘路径。
    private_key_material: str | None = None
    private_key_path = Path(args["private_key_path"]) if args.get("private_key_path") else None
    sm = SecretManager.instance()
    secret_material = None
    if sm.enabled and not private_key_path and not host_config.password:
        # 仅在「无磁盘私钥 + 无密码」时尝试拉取（避免覆盖显式凭证）
        secret_name = args.get("name") or getattr(host_config, "name", None) or host_config.host
        try:
            secret_material = sm.fetch(secret_name)
            private_key_material = secret_material.as_str()
            ctx.logger.info(
                "[secret] 私钥从 KMS 临时拉取到内存"
                f"（source={secret_material.source}, name={secret_name}），不落盘"
            )
        except SecretProviderError as e:
            ctx.logger.error(f"[secret] 拉取私钥失败: {e}")
            return [TextContent(type="text", text=f"密钥不落地模式：拉取私钥失败：{e}")]
    elif sm.enabled and private_key_path:
        return [
            TextContent(
                type="text",
                text=(
                    "密钥不落地模式已启用（SSH_SECRET_PROVIDER_ENABLED=true），"
                    "禁止使用 private_key_path 指定磁盘私钥文件。请通过 SecretManager 配置凭证。"
                ),
            )
        ]

    try:
        config = ConnectionConfig(
            host=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password,
            auth_method="password" if host_config.password else "private_key",
            timeout=host_config.timeout,
            keepalive_interval=getattr(host_config, "keepalive_interval", 30),
            session_timeout=getattr(host_config, "session_timeout", 7200),
            client_type=client_type,
            strict_host_key_checking=args.get("strict_host_key_checking", True),
            known_hosts_path=args.get("known_hosts_path"),
            accept_new_host_key=args.get("accept_new_host_key", True),
            private_key_path=private_key_path,
            private_key_material=private_key_material,
            passphrase=args.get("passphrase"),
            sudo_password=sudo_password,
        )

        session_info = await ctx.session_manager.create_session(config)

        if ctx.audit:
            ctx.audit.log_connect(
                username=config.username,
                host=config.host,
                port=config.port,
                client_type=config.client_type,
                session_id=session_info.session_id,
                success=True,
            )

        output = (
            f"Connected to {session_info.host}:{session_info.port}\n"
            f"Session ID: {session_info.session_id}\n"
            f"Username: {session_info.username}\n"
            f"Connected at: {session_info.connected_at.isoformat()}"
        )
        if save_config:
            output += "\nConfig saved for future use."

        command = args.get("command")
        if command:
            try:
                command_validator.validate_command(command)
            except SecurityError as e:
                ctx.logger.warning(f"Command blocked by security policy in ssh_connect: {command}")
                if ctx.audit:
                    ctx.audit.log_command(
                        username=config.username,
                        host=config.host,
                        command=command,
                        return_code=-1,
                        stdout_length=0,
                        stderr_length=0,
                        session_id=session_info.session_id,
                        execution_time_ms=0,
                    )
                output += (
                    f"\n\n--- Command Blocked by Security Policy ---\n"
                    f"Command: `{command}`\n"
                    f"Reason: {str(e)}\n"
                )
            else:
                session = await ctx.session_manager.get_session(session_info.session_id)
                result = await session.execute_command(command)
                output += "\n\n--- Command Output ---\n"
                output += f"Exit Code: {result['exit_code']}\n"
                if result["stdout"]:
                    output += f"\n{result['stdout']}"
                if result["stderr"]:
                    output += f"\n--- STDERR ---\n{result['stderr']}"

        return [TextContent(type="text", text=output)]
    except Exception as e:
        ctx.logger.error(f"Connection failed: {e}")
        if ctx.audit:
            ctx.audit.log_connect(
                username=config.username,
                host=config.host,
                port=config.port,
                client_type=config.client_type,
                success=False,
                error_message=str(e),
            )
        return [
            TextContent(
                type="text",
                text=f"Connection failed: {str(e)}\n\n"
                f"Check:\n"
                f"1. Server address and port\n"
                f"2. Username and password/key\n"
                f"3. Network connectivity\n"
                f"4. SSH service is running",
            )
        ]
    finally:
        # 加固点 2：连接建立/失败后立即清零内存中的私钥
        # （paramiko 已在内部把私钥加载为 PKey 对象，原始 PEM 字符串不再需要）
        if secret_material is not None:
            sm.release(secret_material)


async def handle_disconnect(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Merge ssh_disconnect + ssh_list_sessions."""
    session_id = args.get("session_id")

    if session_id:
        await ctx.session_manager.close_session(session_id)
        return [TextContent(type="text", text=f"Session {session_id} closed")]

    sessions = ctx.session_manager.list_sessions()
    if not sessions:
        return [TextContent(type="text", text="No active sessions")]

    output = "Active Sessions:\n"
    for session in sessions:
        output += f"\n- Session ID: {session.session_id}\n"
        output += f"  Host: {session.config.host}:{session.config.port}\n"
        output += f"  Username: {session.config.username}\n"
        output += f"  State: {session.state.value}\n"
        connected_at = session._connected_at.isoformat() if session._connected_at else "N/A"
        output += f"  Connected: {connected_at}\n"
        output += f"  Last Activity: {session._last_activity.isoformat()}\n"

    return [TextContent(type="text", text=output)]
