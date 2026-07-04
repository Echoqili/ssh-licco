"""SSH-LICCO command line interface."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ssh_mcp import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ssh-licco",
        description="SSH-LICCO: Remote server management via MCP and CLI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ssh-licco {__version__}",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=False)

    # exec
    exec_parser = subparsers.add_parser("exec", help="Execute a remote command")
    exec_parser.add_argument("cmd", help="Command to execute")
    exec_parser.add_argument("--host", default=None, help="Remote host")
    exec_parser.add_argument("-u", "--username", default=None, help="SSH username")
    exec_parser.add_argument("--password", default=None, help="SSH password")
    exec_parser.add_argument(
        "--connect-timeout", type=int, default=None, help="Connection timeout in seconds"
    )

    # upload
    upload_parser = subparsers.add_parser("upload", help="Upload a file")
    upload_parser.add_argument("local", help="Local file path")
    upload_parser.add_argument("remote", help="Remote file path")
    upload_parser.add_argument("--host", default=None, help="Remote host")
    upload_parser.add_argument("-u", "--username", default=None, help="SSH username")
    upload_parser.add_argument("--password", default=None, help="SSH password")

    # download
    download_parser = subparsers.add_parser("download", help="Download a file")
    download_parser.add_argument("remote", help="Remote file path")
    download_parser.add_argument("local", help="Local file path")
    download_parser.add_argument("--host", default=None, help="Remote host")
    download_parser.add_argument("-u", "--username", default=None, help="SSH username")
    download_parser.add_argument("--password", default=None, help="SSH password")

    # docker-build
    docker_build_parser = subparsers.add_parser("docker-build", help="Build a Docker image")
    docker_build_parser.add_argument("image", help="Image tag")
    docker_build_parser.add_argument("-c", "--context", default=".", help="Build context")
    docker_build_parser.add_argument("-f", "--dockerfile", default="Dockerfile", help="Dockerfile path")
    docker_build_parser.add_argument("-t", "--timeout", type=int, default=600, help="Build timeout")

    # serve
    subparsers.add_parser("serve", help="Start the MCP server")

    # list-hosts
    subparsers.add_parser("list-hosts", help="List configured hosts")

    return parser


def _load_connection_config(args: argparse.Namespace) -> dict:
    """Load connection config from CLI args or environment variables."""
    host = args.host or os.getenv("SSH_HOST")
    username = args.username or os.getenv("SSH_USER")
    password = args.password or os.getenv("SSH_PASSWORD")
    port = args.port if getattr(args, "port", None) else 22
    timeout = args.connect_timeout if getattr(args, "connect_timeout", None) else 30

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "timeout": timeout,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.subcommand is None:
        parser.print_help()
        return 0

    if args.subcommand == "serve":
        from ssh_mcp.server import run_server

        run_server()
        return 0

    if args.subcommand == "list-hosts":
        from ssh_mcp.config_manager import ConfigManager

        manager = ConfigManager()
        hosts = manager.list_hosts()
        if not hosts:
            print("No hosts configured.")
            return 0
        for name, config in hosts.items():
            print(f"{name}: {config.host}:{config.port} ({config.username})")
        return 0

    if args.subcommand == "exec":
        config = _load_connection_config(args)
        print(f"Would execute on {config['host']}: {args.cmd}")
        return 0

    if args.subcommand == "upload":
        config = _load_connection_config(args)
        print(f"Would upload {args.local} -> {config['host']}:{args.remote}")
        return 0

    if args.subcommand == "download":
        config = _load_connection_config(args)
        print(f"Would download {config['host']}:{args.remote} -> {args.local}")
        return 0

    if args.subcommand == "docker-build":
        print(f"Would build Docker image {args.image} from {args.context}/{args.dockerfile}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
