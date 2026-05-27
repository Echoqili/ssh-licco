---
name: "ssh-mcp-ops"
description: "SSH MCP operations guide. Invoke when user needs to perform SSH server operations like connecting, executing commands, file transfer, or Docker management."
---

# SSH MCP Operations Guide

## Quick Reference

### Quick Login (using saved config or env vars)

```
SSH 登录
```

Or with a command after login:
```
SSH 登录，command=ls -la /
```

### Connect with Full Control

```
连接 SSH，host=43.143.207.242, username=root, password=xxx
```

Or using configured server:
```
连接 SSH，name=production
```

### Execute Command

```
执行命令，command=ls -la /, session_id=xxx
```

### Execute with Wait (medium tasks)

```
等待执行命令，command=apt update, session_id=xxx, timeout=60
```

### File Transfer

```
传输文件，local_path=/local/file.txt, remote_path=/remote/file.txt, direction=upload, session_id=xxx
```

### Background Task

```
后台任务，command=docker build -t myapp ., session_id=xxx
```

### Docker Operations

```
构建 Docker 镜像，image_name=myapp:latest, session_id=xxx

检查 Docker 状态，session_id=xxx

查看容器日志，container_name=myapp, session_id=xxx
```

## MCP Tool Parameters

### ssh_login
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| command | No | - | Optional command to execute after login |

### ssh_connect
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| host | No* | - | Server IP/hostname |
| port | No | 22 | SSH port |
| username | No | root | SSH username |
| password | No | - | SSH password |
| private_key_path | No | - | Path to private key |
| passphrase | No | - | Passphrase for encrypted key |
| auth_method | No | private_key | password/private_key/agent |
| name | No | - | Server name from config |
| client_type | No | asyncssh | Client type |
| strict_host_key_checking | No | true | Enable strict host key verification |
| known_hosts_path | No | - | Path to known_hosts file |
| accept_new_host_key | No | false | Auto-accept new host keys (testing only) |

### ssh_execute
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID from connect/login |
| command | Yes | - | Command to execute |
| timeout | No | 30 | Command timeout in seconds |
| background | No | auto | Run in background (auto-detected if not set) |

### ssh_execute_wait
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| command | Yes | - | Command to execute |
| timeout | No | 60 | Maximum wait time in seconds |

### ssh_file_transfer
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| local_path | Yes | - | Local file path |
| remote_path | Yes | - | Remote file path |
| direction | Yes | - | upload/download |

### ssh_background_task
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| command | Yes | - | Command to execute in background |
| workdir | No | /tmp | Working directory |
| log_file | No | /tmp/background_task.log | Log file path |
| wait | No | false | Wait for task completion |
| wait_timeout | No | 60 | Max wait time when wait=true |

### ssh_task_status
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| task_id | Yes | - | Task ID from ssh_background_task |

### ssh_docker_build
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| image_name | Yes | - | Docker image name:tag |
| dockerfile_path | No | ./Dockerfile | Dockerfile path |
| context | No | . | Build context directory |

### ssh_docker_status
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| image_name | No | - | Optional image name to check |

### ssh_container_logs
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| session_id | Yes | - | Session ID |
| container_name | Yes | - | Container name or ID |
| tail | No | 100 | Number of lines to retrieve |
| since | No | - | Optional timestamp filter |

### ssh_list_sessions
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| (none) | - | - | Lists all active sessions |

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

## Server Management

### List Servers
```
列出 SSH 服务器
```

### Add Server
```
添加 SSH 服务器，name=prod, host=43.143.207.242, username=root, password=xxx
```

### Remove Server
```
删除 SSH 服务器，name=prod
```

### List Active Sessions
```
列出 SSH 会话
```

### Disconnect Session
```
断开 SSH，session_id=xxx
```

## SSH Key Authentication

### Generate Key
```
生成 SSH 密钥，key_type=ed25519, comment=mykey
```

### Connect with Key
```
连接 SSH，host=xxx, username=ubuntu, private_key_path=/path/to/key, auth_method=private_key
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
1. SSH 登录
2. 执行命令，command=sudo apt update && sudo apt install -y nginx
3. 执行命令，command=sudo systemctl enable nginx && sudo systemctl start nginx
4. 执行命令，command=curl localhost
```

### File Backup
```
1. 连接 SSH，host=xxx, username=xxx, password=xxx
2. 传输文件，local_path=./backup.tar.gz, remote_path=/backup/backup.tar.gz, direction=upload
3. 执行命令，command=cd /backup && tar -xzf backup.tar.gz
```

### Docker Deployment
```
1. 连接 SSH，host=xxx, username=xxx, password=xxx
2. 构建 Docker 镜像，image_name=myapp:latest, session_id=xxx
3. 检查 Docker 状态，session_id=xxx
4. 执行命令，command=docker run -d -p 8080:80 myapp:latest
5. 查看容器日志，container_name=myapp, session_id=xxx
```

### Background Task
```
1. 连接 SSH，host=xxx, username=xxx, password=xxx
2. 后台任务，command=python train.py, session_id=xxx, wait=true, wait_timeout=300
3. Or check status: 查看任务状态，task_id=xxx, session_id=xxx
```