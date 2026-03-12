---
name: "ssh-mcp-ops"
description: "SSH MCP operations guide. Invoke when user needs to perform SSH server operations like connecting, executing commands, file transfer, or Docker management."
---

# SSH MCP Operations Guide

## Quick Reference

### Connect to Server

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

### File Transfer

```
传输文件，local_path=/local/file.txt, remote_path=/remote/file.txt, direction=upload, session_id=xxx
```

### Docker Operations

```
构建 Docker 镜像，context=., dockerfile_path=./Dockerfile, image_name=myapp:latest, session_id=xxx

检查 Docker 状态，session_id=xxx, image_name=myapp:latest
```

## Common Commands

### System Info
```bash
# Check system info
uname -a

# Check disk usage
df -h

# Check memory
free -h

# Check CPU
top -bn1 | head -20
```

### Network
```bash
# Check IP
ip addr

# Check network connections
netstat -tuln

# Check port
netstat -tuln | grep 22
```

### Process
```bash
# Check processes
ps aux

# Check specific process
ps aux | grep nginx

# Kill process
kill -9 <PID>
```

### Service Management
```bash
# Check service status
systemctl status sshd

# Restart service
sudo systemctl restart sshd

# Check logs
sudo journalctl -u sshd -n 50
```

## MCP Tool Parameters

### ssh_connect
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| host | No* | - | Server IP/hostname |
| port | No | 22 | SSH port |
| username | No | root | SSH username |
| password | No | - | SSH password |
| name | No | - | Server name from config |
| client_type | No | paramiko | Client type |

### ssh_execute
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| command | Yes | - | Command to execute |
| session_id | Yes | - | Session ID from connect |
| timeout | No | 30 | Command timeout |

### ssh_file_transfer
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| local_path | Yes | - | Local file path |
| remote_path | Yes | - | Remote file path |
| direction | Yes | - | upload/download |
| session_id | Yes | - | Session ID |

### ssh_docker_build
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| context | Yes | - | Build context path |
| image_name | Yes | - | Docker image name:tag |
| session_id | Yes | - | Session ID |
| dockerfile_path | No | ./Dockerfile | Dockerfile path |

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

## Troubleshooting

### Connection Timeout
- Check server SSH service: `systemctl status sshd`
- Check firewall: `firewall-cmd --list-all`
- Check port: `netstat -tuln | grep 22`

### Authentication Failed
- Verify username/password
- Check SSH config: `/etc/ssh/sshd_config`
- Check auth logs: `tail -f /var/log/secure`

### Command Timeout
- Increase timeout parameter
- Check server load: `uptime`
- Check process: `ps aux | grep <command>`

## SSH Key Authentication

### Generate Key
```
生成 SSH 密钥，key_type=ed25519, comment=mykey
```

### Setup Key Authentication
```bash
# On local machine
ssh-keygen -t ed25519

# Copy to server
ssh-copy-id user@server

# Or manually
cat ~/.ssh/id_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## Session Management

### View Active Sessions
```
列出 SSH 服务器  # Shows MCP config
# Sessions are managed in memory
```

### Disconnect Session
```
断开 SSH，session_id=xxx
```

## Examples

### Web Server Deployment
```
1. 连接 SSH，host=43.143.207.242, username=root, password=xxx
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
2. 构建 Docker 镜像，context=., image_name=myapp:latest, session_id=xxx
3. 检查 Docker 状态，session_id=xxx, image_name=myapp:latest
4. 执行命令，command=docker run -d -p 8080:80 myapp:latest
```
