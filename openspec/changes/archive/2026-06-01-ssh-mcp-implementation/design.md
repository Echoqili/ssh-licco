## Context

The ssh-licco project implements an MCP server that exposes SSH remote management capabilities as MCP tools. It uses paramiko for SSH connectivity and exposes 7 core tools: ssh_connect, ssh_execute, ssh_disconnect, ssh_file_transfer, ssh_host, ssh_docker, ssh_generate_key.

## Goals / Non-Goals

**Goals:**
- Provide SSH connection management with password, private key, and agent authentication
- Enable secure command execution with multiple security levels
- Support background task execution for long-running commands
- Implement session lifecycle management with keepalive and timeout cleanup
- Provide SFTP file transfer capabilities
- Support Docker management
- Allow SSH key pair generation
- Manage host configurations
- Enforce rate limiting
- Optional audit logging

**Non-Goals:**
- Not a general-purpose SSH client
- No shell terminal/PTY support
- No SCP protocol support
- No multi-hop SSH/proxy jump support

## Decisions

- **Paramiko as SSH client**: Chosen for synchronous API compatibility
- **ThreadPoolExecutor**: Wraps paramiko's blocking API
- **Session-based architecture**: UUID-based session_id, SessionManager
- **Security levels via environment**: STRICT/BALANCED/RELAXED
- **Configuration priority**: User > named host > env vars
- **Background execution**: Pattern matching + nohup with PID tracking

## Risks / Trade-offs

- Synchronous SSH calls add complexity
- Command-based Docker integration is simpler but less type-safe
- Pattern-based background detection may miss edge cases
- AutoAddPolicy skips host key verification