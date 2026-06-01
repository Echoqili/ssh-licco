## Why

The ssh-licco project provides SSH remote server management through the MCP protocol, enabling AI models to securely manage remote servers.

## What Changes

- SSH connection management with multiple auth methods
- Command execution with security validation
- Session lifecycle management
- SFTP file transfer support
- Docker container management
- SSH key pair generation
- Host configuration management
- Security features: validation, rate limiting, audit logging

## Impact

- 7 MCP tools exposed via server.py
- Dependencies: asyncssh, mcp SDK, pydantic
- Configuration via env vars and hosts.json