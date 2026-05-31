---
name: "ssh-mcp-ops"
description: "SSH MCP operations guide. Invoke when user needs to perform SSH server operations like connecting, executing commands, file transfer, or Docker management."
---

# SSH MCP Operations Guide

## Tool Calling Priority

When executing server operations, tools must be called in the following priority order:

```
1️⃣ MCP Tools (ssh_connect, ssh_execute, etc.)  ← Always use first
         ↓ If MCP tools are unavailable/not loaded in current session
2️⃣ CLI Tool (ssh-licco exec)                    ← Second choice
         │ Note: Use SSH_SECURITY_LEVEL=relaxed mode
         │       Set SSH_EXTRA_ALLOWED_COMMANDS for non-whitelist commands
         ↓ If CLI tool is also not available
3️⃣ Python Paramiko Script                        ← Last resort
```

### How to determine which layer to use

| Indicator | Use |
|-----------|-----|
| MCP tools appear in your tool list | **1️⃣ MCP tools** - direct invocation |
| MCP tools not in tool list, but `ssh-licco` command works | **2️⃣ CLI** - `ssh-licco exec` with relaxed mode |
| Neither MCP nor CLI available | **3️⃣ Python paramiko** - write inline Python script |

### CLI usage pattern

```powershell
# Set relaxed mode to allow pipes, redirects, etc.
$env:SSH_SECURITY_LEVEL="relaxed"

# Set extra allowed commands for non-default tools
$env:SSH_EXTRA_ALLOWED_COMMANDS="pg_isready,psql"

# Execute command
ssh-licco exec --host <ip> -u <user> --password <pwd> "<command>"
```

## 7 Core Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `ssh_connect` | Connect to SSH server (auto-reads env vars / saved config) |
| 2 | `ssh_execute` | Execute commands (auto-connect, background, long tasks) |
| 3 | `ssh_disconnect` | Disconnect or list active sessions |
| 4 | `ssh_file_transfer` | Upload/download/list files via SFTP |
| 5 | `ssh_host` | Manage server configs (list/add/remove) |
| 6 | `ssh_docker` | Docker management (ps/images/build/logs) |
| 7 | `ssh_generate_key` | Generate SSH key pairs |

## Quick Reference

### Connect (auto-login with env vars)

```
ssh_connect
```

Or with params:
```
ssh_connect, host=43.143.207.242, username=root, password=xxx
```

Or using saved config:
```
ssh_connect, name=production
```

Connect and run a command:
```
ssh_connect, command=ls -la /
```

### Execute Command

```
ssh_execute, session_id=xxx, command=ls -la /
```

No session_id (auto-connect via env vars):
```
ssh_execute, command=redis-cli KEYS '*'
```

### Background Task

```
ssh_execute, session_id=xxx, command=docker build -t myapp ., background=true
```

With wait for completion:
```
ssh_execute, session_id=xxx, command=python train.py, background=true, wait=true, wait_timeout=300
```

### File Transfer

```
ssh_file_transfer, session_id=xxx, local_path=/local/file.txt, remote_path=/remote/file.txt, direction=upload
```

### Docker Operations

```
ssh_docker, session_id=xxx, action=ps
ssh_docker, session_id=xxx, action=images, image_name=myapp
ssh_docker, session_id=xxx, action=build, image_name=myapp:latest
ssh_docker, session_id=xxx, action=logs, container_name=myapp, tail=100
```

### Server Management

```
ssh_host, action=list
ssh_host, action=add, name=prod, host=43.143.207.242, username=root, password=xxx
ssh_host, action=remove, name=prod
```

### Session Management

```
ssh_disconnect                          # List all sessions
ssh_disconnect, session_id=xxx          # Close specific session
```

### Generate Key

```
ssh_generate_key, key_type=ed25519, comment=mykey
ssh_generate_key, key_type=rsa, key_size=4096, save_path=~/.ssh/id_rsa
```

## MCP Tool Parameters

### ssh_connect
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| host | No | - | Server IP/hostname. Omit to auto-read env vars |
| port | No | 22 | SSH port |
| username | No | root | SSH username |
| password | No | - | SSH password |
| private_key_path | No | - | Path to private key |
| passphrase | No | - | Passphrase for encrypted key |
| auth_method | No | private_key | password/private_key/agent |
| name | No | - | Server name from config/hosts.json |
| save_config | No | false | Save to local config |
| command | No | - | Optional command to execute after connecting |
| accept_new_host_key | No | true | Auto-accept new host keys |

### ssh_execute
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | No | - | Session ID. Omit to auto-connect via env vars |
| command | Yes | - | Command to execute |
| timeout | No | 30 | Command timeout in seconds |
| background | No | auto | Run in background (auto-detected) |
| workdir | No | /tmp | Working directory for background tasks |
| log_file | No | /tmp/background_task.log | Log file for background output |
| wait | No | false | Wait for background task completion |
| wait_timeout | No | 60 | Max wait time when wait=true |

### ssh_disconnect
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | No | - | Session to close. Omit to list all sessions |

### ssh_file_transfer
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| local_path | Yes | - | Local file path |
| remote_path | Yes | - | Remote file path |
| direction | Yes | - | upload/download/list |

### ssh_host
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| action | Yes | - | list/add/remove |
| name | For add/remove | - | Server name |
| host | For add | - | Server IP/hostname |
| port | No | 22 | SSH port |
| username | No | root | SSH username |
| password | No | - | SSH password |
| timeout | No | 60 | Connection timeout |

### ssh_docker
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| action | Yes | - | ps/images/build/logs |
| image_name | For build | - | Image name (build: required, images: optional filter) |
| container_name | For logs | - | Container name or ID |
| dockerfile_path | No | ./Dockerfile | Dockerfile path |
| context | No | . | Build context directory |
| tail | No | 100 | Log lines to retrieve |

### ssh_generate_key
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| key_type | No | ed25519 | rsa/ed25519 |
| key_size | No | 4096 | Key size for RSA |
| comment | No | - | Key comment |
| save_path | No | - | Path to save key files |

## Common Commands

### System Info
```bash
uname -a
df -h
free -h
top -bn1 | head -20
```

### Network
```bash
ip addr
netstat -tuln
ss -tuln | grep 22
```

### Process
```bash
ps aux
ps aux | grep nginx
kill -9 <PID>
```

### Service Management
```bash
systemctl status sshd
sudo systemctl restart sshd
sudo journalctl -u sshd -n 50
```

## Auto Background Detection

`ssh_execute` automatically detects long-running commands and runs them in background:
- Web servers: `python app.py`, `npm start`, `uvicorn`, etc.
- Database servers: `mongod`, `mysql`, `redis-server`
- Docker compose: `docker-compose up`
- Service starts: `systemctl start xxx`
- Java apps: `java -jar`, `mvn spring-boot:run`
- And many more patterns

Instant commands like `docker ps`, `ls`, `cat`, `git status` are NOT run in background.

## Security Notes

- Commands are validated against security policy (`SSH_SECURITY_LEVEL`)
- Blocked commands show helpful resolution instructions
- Rate limiting prevents DoS (configurable via env vars)
- Audit logging available via `SSH_AUDIT_LOG_PATH`

## Examples

### Web Server Deployment
```
1. ssh_connect
2. ssh_execute, command=sudo apt update && sudo apt install -y nginx
3. ssh_execute, command=sudo systemctl enable nginx && sudo systemctl start nginx
4. ssh_execute, command=curl localhost
```

### File Backup
```
1. ssh_connect, host=xxx, username=xxx, password=xxx
2. ssh_file_transfer, local_path=./backup.tar.gz, remote_path=/backup/backup.tar.gz, direction=upload
3. ssh_execute, command=cd /backup && tar -xzf backup.tar.gz
```

### Docker Deployment
```
1. ssh_connect, host=xxx, username=xxx, password=xxx
2. ssh_docker, action=build, image_name=myapp:latest
3. ssh_docker, action=ps
4. ssh_execute, command=docker run -d -p 8080:80 myapp:latest
5. ssh_docker, action=logs, container_name=myapp
```

### Background Task
```
1. ssh_connect
2. ssh_execute, command=python train.py, background=true, wait=true, wait_timeout=300
```