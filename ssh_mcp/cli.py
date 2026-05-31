#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from . import __version__


def _load_connection_config(args) -> dict:
    config = {
        "host": getattr(args, "host", None) or os.getenv("SSH_HOST", ""),
        "port": getattr(args, "port", None) or int(os.getenv("SSH_PORT", "22")),
        "username": getattr(args, "username", None) or os.getenv("SSH_USER", "root"),
        "password": getattr(args, "password", None) or os.getenv("SSH_PASSWORD", ""),
        "timeout": getattr(args, "connect_timeout", None) or int(os.getenv("SSH_TIMEOUT", "60")),
        "keepalive_interval": int(os.getenv("SSH_KEEPALIVE_INTERVAL", "30")),
        "session_timeout": int(os.getenv("SSH_SESSION_TIMEOUT", "7200")),
        "client_type": os.getenv("SSH_CLIENT_TYPE", "paramiko"),
    }

    if not config["host"]:
        try:
            from .config_manager import ConfigManager
            cm = ConfigManager()
            saved = cm.load()
            if saved:
                config["host"] = saved.host
                config["port"] = saved.port
                config["username"] = saved.username
                if saved.password and not config["password"]:
                    config["password"] = saved.password
        except Exception:
            pass

    if not config["host"]:
        print("Error: SSH host not configured. Use --host or set SSH_HOST env var.", file=sys.stderr)
        sys.exit(1)

    if not config["password"]:
        print("Error: SSH password not configured. Use --password or set SSH_PASSWORD env var.", file=sys.stderr)
        sys.exit(1)

    return config


def _make_connection_config(config: dict):
    from .connection_config import ConnectionConfig

    return ConnectionConfig(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        auth_method="password",
        timeout=config["timeout"],
        keepalive_interval=config["keepalive_interval"],
        session_timeout=config["session_timeout"],
        client_type=config["client_type"],
        strict_host_key_checking=False,
        accept_new_host_key=True,
    )


async def _connect_and_exec(config: dict, command: str, timeout: int = 30) -> dict:
    from .session_manager import SSHSession

    conn_config = _make_connection_config(config)
    session = SSHSession(conn_config)

    try:
        await session.connect()
        result = await session.execute_command(command, timeout=timeout)
        return result
    finally:
        try:
            await session.disconnect()
        except Exception:
            pass


async def _cmd_exec(args):
    config = _load_connection_config(args)
    command = args.cmd
    timeout = args.timeout

    try:
        from .security import SecurityError, command_validator
        command_validator.validate_command(command)
    except SecurityError as e:
        print(f"Security: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = await _connect_and_exec(config, command, timeout)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    if result.get("stdout"):
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)

    sys.exit(result.get("exit_code", 1))


async def _cmd_upload(args):
    config = _load_connection_config(args)
    local_path = args.local
    remote_path = args.remote

    from .session_manager import SSHSession

    conn_config = _make_connection_config(config)
    session = SSHSession(conn_config)

    try:
        await session.connect()
        result = await session.upload_file(local_path, remote_path)
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            await session.disconnect()
        except Exception:
            pass

    if result.get("success"):
        print(f"Uploaded: {local_path} -> {remote_path}")
        sys.exit(0)
    else:
        print(f"Upload failed: {result.get('message', 'unknown error')}", file=sys.stderr)
        sys.exit(1)


async def _cmd_download(args):
    config = _load_connection_config(args)
    remote_path = args.remote
    local_path = args.local

    from .session_manager import SSHSession

    conn_config = _make_connection_config(config)
    session = SSHSession(conn_config)

    try:
        await session.connect()
        result = await session.download_file(remote_path, local_path)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            await session.disconnect()
        except Exception:
            pass

    if result.get("success"):
        print(f"Downloaded: {remote_path} -> {local_path}")
        sys.exit(0)
    else:
        print(f"Download failed: {result.get('message', 'unknown error')}", file=sys.stderr)
        sys.exit(1)


async def _cmd_docker_build(args):
    config = _load_connection_config(args)
    image_name = args.image
    context = args.context
    dockerfile = args.dockerfile

    build_cmd = f"cd {context} && docker build -t {image_name} -f {dockerfile} ."

    try:
        from .security import SecurityError, command_validator
        command_validator.validate_command(build_cmd)
    except SecurityError as e:
        print(f"Security: {e}", file=sys.stderr)
        sys.exit(1)

    timeout = args.timeout
    print(f"Building Docker image: {image_name}")
    print(f"Context: {context}, Dockerfile: {dockerfile}")
    print("---")

    try:
        result = await _connect_and_exec(config, build_cmd, timeout)
    except Exception as e:
        print(f"Docker build failed: {e}", file=sys.stderr)
        sys.exit(1)

    if result.get("stdout"):
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)

    exit_code = result.get("exit_code", 1)
    if exit_code == 0:
        print(f"\nBuild succeeded: {image_name}")
    else:
        print(f"\nBuild failed with exit code: {exit_code}", file=sys.stderr)

    sys.exit(exit_code)


async def _cmd_list_hosts(args):
    from .config_manager import ConfigManager

    cm = ConfigManager()
    hosts = cm.list_hosts()

    output = {"env": None, "hosts": []}

    if os.getenv("SSH_HOST"):
        output["env"] = {
            "host": os.getenv("SSH_HOST"),
            "port": os.getenv("SSH_PORT", "22"),
            "username": os.getenv("SSH_USER", "root"),
        }

    for h in hosts:
        output["hosts"].append({
            "name": h.name,
            "host": h.host,
            "port": h.port,
            "username": h.username,
        })

    print(json.dumps(output, indent=2))


def _add_connection_args(parser: argparse.ArgumentParser):
    parser.add_argument("--host", help="SSH host (or set SSH_HOST env)")
    parser.add_argument("--port", "-p", type=int, help="SSH port (default: 22)")
    parser.add_argument("--username", "-u", help="SSH username (or set SSH_USER env)")
    parser.add_argument("--password", help="SSH password (or set SSH_PASSWORD env)")
    parser.add_argument("--connect-timeout", type=int, default=60, help="Connection timeout in seconds (default: 60)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssh-licco",
        description="SSH LICCO - CLI for remote server management via SSH",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="subcommand", help="Available commands")

    # exec
    p_exec = sub.add_parser("exec", help="Execute a command on remote server")
    _add_connection_args(p_exec)
    p_exec.add_argument("cmd", help="Command to execute")
    p_exec.add_argument("--timeout", "-t", type=int, default=60, help="Command timeout in seconds")

    # upload
    p_upload = sub.add_parser("upload", help="Upload a file to remote server")
    _add_connection_args(p_upload)
    p_upload.add_argument("local", help="Local file path")
    p_upload.add_argument("remote", help="Remote file path")

    # download
    p_download = sub.add_parser("download", help="Download a file from remote server")
    _add_connection_args(p_download)
    p_download.add_argument("remote", help="Remote file path")
    p_download.add_argument("local", help="Local file path")

    # docker-build
    p_docker = sub.add_parser("docker-build", help="Build a Docker image on remote server")
    _add_connection_args(p_docker)
    p_docker.add_argument("image", help="Docker image name and tag (e.g. myapp:latest)")
    p_docker.add_argument("--context", "-c", default=".", help="Build context directory (default: .)")
    p_docker.add_argument("--dockerfile", "-f", default="./Dockerfile", help="Path to Dockerfile (default: ./Dockerfile)")
    p_docker.add_argument("--timeout", "-t", type=int, default=300, help="Build timeout in seconds (default: 300)")

    # list-hosts
    p_hosts = sub.add_parser("list-hosts", help="List configured SSH hosts")
    p_hosts.add_argument("--json", action="store_true", help="Output as JSON")

    # serve (MCP server mode)
    sub.add_parser("serve", help="Start MCP server (stdio mode)")

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        from .server import run_server
        run_server()
        return

    if args.subcommand == "serve":
        from .server import run_server
        run_server()
        return

    cmd_map = {
        "exec": _cmd_exec,
        "upload": _cmd_upload,
        "download": _cmd_download,
        "docker-build": _cmd_docker_build,
        "list-hosts": _cmd_list_hosts,
    }

    handler = cmd_map.get(args.subcommand)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
