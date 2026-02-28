from __future__ import annotations

import asyncio
from typing import Any
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .connection_config import ConnectionConfig
from .session_manager import SessionManager, SessionInfo
from .key_manager import KeyManager
from .config_manager import ConfigManager, SSHConfig, SSHHost


class SSHMCPServer:
    def __init__(self):
        self.server = Server("ssh-licco", "0.1.0")
        self.session_manager = SessionManager()
        self.key_manager = KeyManager()
        self.config_manager = ConfigManager()
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="ssh_config",
                    description="Configure SSH connection (host, port, username, password). Save to config file for easy login.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server IP or hostname", "default": "127.0.0.1"},
                            "port": {"type": "integer", "description": "SSH server port", "default": 22},
                            "username": {"type": "string", "description": "SSH username", "default": "root"},
                            "password": {"type": "string", "description": "SSH password"},
                            "timeout": {"type": "integer", "description": "Connection timeout (seconds)", "default": 30}
                        },
                        "required": ["password"]
                    }
                ),
                Tool(
                    name="ssh_login",
                    description="Login to SSH server using saved configuration (no parameters needed if config exists)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute after login (optional)"}
                        }
                    }
                ),
                Tool(
                    name="ssh_connect",
                    description="Establish an SSH connection to a remote server",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH server hostname or IP (or use name to connect via server.json config)"},
                            "port": {"type": "integer", "description": "SSH server port (default: 22)", "default": 22},
                            "username": {"type": "string", "description": "SSH username"},
                            "password": {"type": "string", "description": "SSH password (optional if using key auth)"},
                            "private_key_path": {"type": "string", "description": "Path to private key file"},
                            "passphrase": {"type": "string", "description": "Passphrase for private key"},
                            "auth_method": {"type": "string", "enum": ["password", "private_key", "agent"], "default": "private_key"},
                            "name": {"type": "string", "description": "Connect using host from server.json by name"}
                        }
                    }
                ),
                Tool(
                    name="ssh_list_hosts",
                    description="List all configured SSH hosts from server.json",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_execute",
                    description="Execute a command on an active SSH session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID from ssh_connect"},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 30}
                        },
                        "required": ["session_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_disconnect",
                    description="Close an SSH session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID to close"}
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="ssh_list_sessions",
                    description="List all active SSH sessions",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="ssh_generate_key",
                    description="Generate a new SSH key pair",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key_type": {"type": "string", "enum": ["rsa", "ed25519"], "default": "ed25519"},
                            "key_size": {"type": "integer", "description": "Key size for RSA (default: 4096)", "default": 4096},
                            "comment": {"type": "string", "description": "Comment for the key"},
                            "save_path": {"type": "string", "description": "Path to save the key"}
                        }
                    }
                ),
                Tool(
                    name="ssh_file_transfer",
                    description="Transfer files via SFTP",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session ID"},
                            "local_path": {"type": "string", "description": "Local file path"},
                            "remote_path": {"type": "string", "description": "Remote file path"},
                            "direction": {"type": "string", "enum": ["upload", "download"], "description": "Transfer direction"}
                        },
                        "required": ["session_id", "local_path", "remote_path", "direction"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            try:
                if name == "ssh_config":
                    return await self._handle_config(arguments)
                elif name == "ssh_login":
                    return await self._handle_login(arguments)
                elif name == "ssh_connect":
                    return await self._handle_connect(arguments)
                elif name == "ssh_execute":
                    return await self._handle_execute(arguments)
                elif name == "ssh_disconnect":
                    return await self._handle_disconnect(arguments)
                elif name == "ssh_list_sessions":
                    return await self._handle_list_sessions(arguments)
                elif name == "ssh_generate_key":
                    return await self._handle_generate_key(arguments)
                elif name == "ssh_file_transfer":
                    return await self._handle_file_transfer(arguments)
                elif name == "ssh_list_hosts":
                    return await self._handle_list_hosts(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_config(self, args: dict) -> list[TextContent]:
        config = SSHConfig(
            host=args.get("host", "127.0.0.1"),
            port=args.get("port", 22),
            username=args.get("username", "root"),
            password=args.get("password", ""),
            timeout=args.get("timeout", 30)
        )
        self.config_manager.save(config)
        return [TextContent(
            type="text",
            text=f"SSH配置已保存:\n"
                 f"主机: {config.host}:{config.port}\n"
                 f"用户名: {config.username}\n"
                 f"配置文件: {self.config_manager.config_path}"
        )]

    async def _handle_login(self, args: dict) -> list[TextContent]:
        config_data = self.config_manager.load()
        if not config_data:
            return [TextContent(
                type="text",
                text="请先使用 ssh_config 工具配置SSH连接信息"
            )]
        
        if not config_data.password:
            return [TextContent(type="text", text="密码未配置，请先使用 ssh_config 设置密码")]
        
        config = ConnectionConfig(
            host=config_data.host,
            port=config_data.port,
            username=config_data.username,
            password=config_data.password,
            auth_method="password",
            timeout=config_data.timeout
        )
        
        session_info = await self.session_manager.create_session(config)
        
        output = f"SSH登录成功!\n"
        output += f"主机: {session_info.host}:{session_info.port}\n"
        output += f"Session ID: {session_info.session_id}\n"
        output += f"用户名: {session_info.username}\n"
        output += f"连接时间: {session_info.connected_at.isoformat()}"
        
        command = args.get("command")
        if command:
            session = await self.session_manager.get_session(session_info.session_id)
            result = await session.execute_command(command)
            output += f"\n\n--- 命令输出 ---\n"
            output += f"Exit Code: {result['exit_code']}\n"
            if result["stdout"]:
                output += f"\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n--- 错误 ---\n{result['stderr']}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_connect(self, args: dict) -> list[TextContent]:
        host_config = None
        
        if args.get("name"):
            host_config = self.config_manager.get_host_by_name(args["name"])
            if not host_config:
                return [TextContent(type="text", text=f"Host '{args['name']}' not found in server.json")]
        
        if host_config:
            config = ConnectionConfig(
                host=host_config.host,
                port=host_config.port,
                username=host_config.username,
                password=host_config.password,
                auth_method="password" if host_config.password else "private_key",
                timeout=host_config.timeout
            )
        else:
            config = ConnectionConfig(
                host=args["host"],
                port=args.get("port", 22),
                username=args["username"],
                password=args.get("password"),
                private_key_path=Path(args["private_key_path"]) if args.get("private_key_path") else None,
                passphrase=args.get("passphrase"),
                auth_method=args.get("auth_method", "private_key")
            )
        
        session_info = await self.session_manager.create_session(config)
        
        return [TextContent(
            type="text",
            text=f"Successfully connected to {session_info.host}:{session_info.port}\n"
                 f"Session ID: {session_info.session_id}\n"
                 f"Username: {session_info.username}\n"
                 f"Connected at: {session_info.connected_at.isoformat()}"
        )]

    async def _handle_execute(self, args: dict) -> list[TextContent]:
        session = await self.session_manager.get_session(args["session_id"])
        if not session:
            return [TextContent(type="text", text=f"Session not found: {args['session_id']}")]
        
        timeout = args.get("timeout", 30)
        result = await session.execute_command(args["command"], timeout=timeout)
        
        output = f"Exit Code: {result['exit_code']}\n"
        if result["stdout"]:
            output += f"\n--- STDOUT ---\n{result['stdout']}"
        if result["stderr"]:
            output += f"\n--- STDERR ---\n{result['stderr']}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_disconnect(self, args: dict) -> list[TextContent]:
        session_id = args["session_id"]
        await self.session_manager.close_session(session_id)
        return [TextContent(type="text", text=f"Session {session_id} closed")]

    async def _handle_list_sessions(self, args: dict) -> list[TextContent]:
        sessions = self.session_manager.list_sessions()
        
        if not sessions:
            return [TextContent(type="text", text="No active sessions")]
        
        output = "Active Sessions:\n"
        for session in sessions:
            output += f"\n- Session ID: {session.session_id}\n"
            output += f"  Host: {session.host}:{session.port}\n"
            output += f"  Username: {session.username}\n"
            output += f"  State: {session.state.value}\n"
            output += f"  Connected: {session.connected_at.isoformat()}\n"
        
        return [TextContent(type="text", text=output)]

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

    async def _handle_file_transfer(self, args: dict) -> list[TextContent]:
        session = await self.session_manager.get_session(args["session_id"])
        if not session:
            return [TextContent(type="text", text=f"Session not found: {args['session_id']}")]
        
        direction = args.get("direction", "upload")
        local_path = args.get("local_path", "")
        remote_path = args.get("remote_path", "")
        
        if direction == "upload":
            result = await session.upload_file(local_path, remote_path)
        elif direction == "download":
            result = await session.download_file(remote_path, local_path)
        elif direction == "list":
            result = await session.list_directory(remote_path or ".")
        else:
            return [TextContent(type="text", text=f"Unknown direction: {direction}")]
        
        if result.get("success"):
            output = f"✅ {result.get('message', 'Success')}"
            if "files" in result:
                output = f"📁 Files in {result.get('path', '.')}:\n"
                for f in result["files"]:
                    output += f"  - {f}\n"
        else:
            output = f"❌ {result.get('message', 'Failed')}"
        
        return [TextContent(type="text", text=output)]

    async def _handle_list_hosts(self, args: dict) -> list[TextContent]:
        hosts = self.config_manager.list_hosts()
        
        if not hosts:
            return [TextContent(type="text", text="No SSH hosts configured in server.json")]
        
        output = "Configured SSH Hosts:\n"
        for host in hosts:
            output += f"\n- Name: {host.name}\n"
            output += f"  Host: {host.host}:{host.port}\n"
            output += f"  Username: {host.username}\n"
            output += f"  Password: {'***' if host.password else 'N/A'}\n"
        
        return [TextContent(type="text", text=output)]

    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    server = SSHMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
