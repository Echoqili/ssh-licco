---
name: "ssh-mcp-troubleshoot"
description: "SSH MCP troubleshooting guide. Invoke when user encounters connection issues, authentication errors, or needs to diagnose SSH/Docker problems."
---

# SSH MCP Troubleshooting Guide

## Quick Diagnostics

### Check SSH Connection
```bash
ping -c 4 43.143.207.242
nc -zv 43.143.207.242 22
telnet 43.143.207.242 22
```

### Check Server Status
```bash
systemctl status sshd
systemctl status firewalld
iptables -L -n
df -h
free -m
uptime
```

## Common Issues

### 1. Connection Timeout

**Symptoms**: 
- "Connection timed out"
- "No route to host"

**Solutions**:
1. Check server IP is correct
2. Check server is running
3. Check firewall allows SSH (port 22)
4. Check server has network connectivity
5. Try with longer timeout: `timeout=120`

**MCP Example**:
```
连接 SSH，host=43.143.207.242, username=root, password=xxx, timeout=120
```

### 2. Authentication Failed

**Symptoms**:
- "Authentication failed"
- "Permission denied"

**Solutions**:
1. Verify username is correct
2. Verify password is correct
3. Check SSH config: `PasswordAuthentication yes`
4. Check user exists on server
5. Check user has shell access: `grep username /etc/passwd`

**Server Commands**:
```bash
sudo grep "PasswordAuthentication" /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### 3. Error Reading SSH Protocol Banner

**Symptoms**:
- "Error reading SSH protocol banner"
- "Connection closed by remote host"

**Solutions**:
1. SSH service may be hung - restart it:
   ```bash
   sudo systemctl restart sshd
   ```
2. Check SSH service status:
   ```bash
   sudo systemctl status sshd
   sudo journalctl -u sshd -n 50
   ```
3. Check server load:
   ```bash
   uptime
   top
   ```
4. Check SSH port is responding:
   ```bash
   nc -zv hostname 22
   ```

### 4. Host Key Verification Failed

**Symptoms**:
- "Host key verification failed"
- "Known hosts file error"

**Solutions**:
1. Remove old host key:
   ```bash
   ssh-keygen -R hostname
   ```
2. Or use `accept_new_host_key=true` in ssh_connect (testing only):
   ```
   连接 SSH，host=xxx, accept_new_host_key=true
   ```
3. Or disable strict checking (not recommended for production):
   ```
   连接 SSH，host=xxx, strict_host_key_checking=false
   ```

### 5. Connection Refused

**Symptoms**:
- "Connection refused"
- "No connection could be made"

**Solutions**:
1. SSH service not running:
   ```bash
   sudo systemctl start sshd
   sudo systemctl enable sshd
   ```
2. SSH on different port - check port:
   ```bash
   grep "^Port" /etc/ssh/sshd_config
   ```

### 6. Command Blocked by Security Policy

**Symptoms**:
- "Command blocked by security policy"
- "SecurityError" in output
- Interactive resolution instructions shown

**Solutions**:

**Method 1: Adjust security level (recommended)**
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "relaxed"
      }
    }
  }
}
```

**Method 2: Add extra allowed commands**
```json
{
  "SSH_EXTRA_ALLOWED_COMMANDS": "your-command"
}
```

**Method 3: Add extra allowed patterns (for special characters)**
```json
{
  "SSH_EXTRA_ALLOWED_PATTERNS": "|,>,<,&,;"
}
```

**Security Levels**:
| Level | Env Value | Behavior |
|-------|-----------|----------|
| Strict | `SSH_SECURITY_LEVEL=strict` | Whitelist only |
| Balanced | `SSH_SECURITY_LEVEL=balanced` | Default, blocks dangerous patterns |
| Relaxed | `SSH_SECURITY_LEVEL=relaxed` | Permissive |

### 7. Rate Limit Triggered

**Symptoms**:
- "Rate limit exceeded" message
- "超过 30 次请求/60秒"

**Solutions**:
1. Wait and retry (default: 30 requests per 60 seconds)
2. Adjust limits:
   ```json
   {
     "SSH_RATE_LIMIT_MAX": "60",
     "SSH_RATE_LIMIT_WINDOW": "60"
   }
   ```
3. Disable rate limiting (not recommended for production):
   ```json
   {
     "SSH_RATE_LIMIT": "false"
   }
   ```

### 8. Docker Build Failed

**Symptoms**:
- "Docker build failed"
- "Cannot connect to Docker daemon"

**Solutions**:
1. Check Docker is installed:
   ```bash
   docker --version
   ```
2. Check Docker service:
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```
3. Add user to docker group:
   ```bash
   sudo usermod -aG docker $USER
   ```
4. Check Docker socket permissions:
   ```bash
   ls -la /var/run/docker.sock
   ```

### 9. File Transfer Failed

**Symptoms**:
- "SFTP error"
- "Permission denied"

**Solutions**:
1. Check remote directory exists:
   ```bash
   ls -la /remote/path/
   ```
2. Check write permissions:
   ```bash
   touch /remote/path/test.txt
   ```
3. Use correct path separators (Linux uses / not \)

### 10. Background Task Not Found

**Symptoms**:
- "NOT_FOUND" status when checking task
- PID file missing

**Solutions**:
1. Check if the task command was correct
2. Verify the task_id matches
3. Check if the session is still active:
   ```
   列出 SSH 会话
   ```
4. Check logs directly:
   ```
   执行命令，command=cat /tmp/background_task.log, session_id=xxx
   ```

### 11. Password Conflict Detected

**Symptoms**:
- `ssh_list_hosts` shows password conflict warning
- Different passwords in MCP config vs hosts.json

**Solutions**:
1. Unify passwords across config sources
2. Or use force env mode:
   ```json
   {
     "SSH_FORCE_ENV_CONFIG": "true"
   }
   ```
3. This ensures MCP env config always takes priority

## Diagnostic Commands

### Server Diagnostics
```bash
uname -a
cat /etc/os-release
ip addr
ip route
ss -tuln
df -h
free -h
uptime
top -bn1 | head -15
ps aux | head -20
ps -ef | grep ssh
tail -f /var/log/secure
journalctl -u sshd -n 100
```

### MCP Diagnostics
```python
import json
password = "P/[KY}+wa7?2|uc"
print(json.dumps({"password": password}))
```

### Security Diagnostics
```bash
echo $SSH_SECURITY_LEVEL
echo $SSH_RATE_LIMIT
echo $SSH_EXTRA_ALLOWED_COMMANDS
```

## Health Check Script

Run on remote server:
```bash
#!/bin/bash
echo "=== System Info ==="
uptime
echo ""
echo "=== Disk Usage ==="
df -h
echo ""
echo "=== Memory ==="
free -h
echo ""
echo "=== SSH Service ==="
systemctl status sshd --no-pager
echo ""
echo "=== Network Connections ==="
ss -tuln | grep :22
echo ""
echo "=== Last Login ==="
last -5
```

## Reset SSH Service (Server Side)

```bash
sudo systemctl stop sshd
pkill -9 sshd
rm -rf /run/sshd*
sudo systemctl start sshd
sudo systemctl status sshd
```

## Log Locations

| Service | Log Location |
|---------|-------------|
| SSH | `/var/log/secure` (RHEL/CentOS) |
| SSH | `/var/log/auth.log` (Debian/Ubuntu) |
| Docker | `journalctl -u docker` |
| System | `/var/log/messages` |
| MCP Audit | Configured via `SSH_AUDIT_LOG_PATH` |

## Get Help

### Collect Debug Info
```bash
script debug_session.log
uname -a
df -h
free -h
systemctl status sshd
netstat -tuln | grep 22
echo "Security Level: $SSH_SECURITY_LEVEL"
echo "Rate Limit: $SSH_RATE_LIMIT"
exit
```

### Report Issue
Include:
1. Error message
2. Server IP/hostname
3. OS version: `cat /etc/os-release`
4. SSH version: `ssh -V`
5. `SSH_SECURITY_LEVEL` setting
6. Relevant log excerpts

## Common Server Fixes

### Restart SSH Service
```bash
sudo systemctl restart sshd
```

### Check SSH Config
```bash
sudo sshd -t
sudo systemctl reload sshd
```

### Fix Permissions
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 644 ~/.ssh/known_hosts
```

### Check User Shell
```bash
grep username /etc/passwd
```

### Allow Root Login (if needed)
```bash
sudo nano /etc/ssh/sshd_config
PermitRootLogin yes
PasswordAuthentication yes
sudo systemctl restart sshd
```