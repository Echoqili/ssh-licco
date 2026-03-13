---
name: "ssh-mcp-troubleshoot"
description: "SSH MCP troubleshooting guide. Invoke when user encounters connection issues, authentication errors, or needs to diagnose SSH/Docker problems."
---

# SSH MCP Troubleshooting Guide

## Quick Diagnostics

### Check SSH Connection
```bash
# Test network connectivity
ping -c 4 43.143.207.242

# Test SSH port
nc -zv 43.143.207.242 22
telnet 43.143.207.242 22

# Check SSH banner
openssl s_client -connect 43.143.207.242:22
```

### Check Server Status
```bash
# Server SSH service
systemctl status sshd

# Server firewall
systemctl status firewalld
iptables -L -n

# Server resources
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
# On server
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

3. Check server load - may be too high:
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

2. Or manually edit known_hosts:
   ```bash
   nano ~/.ssh/known_hosts
   # Delete the line with the hostname
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

### 6. Docker Build Failed

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
   # Then logout and login
   ```

4. Check Docker socket permissions:
   ```bash
   ls -la /var/run/docker.sock
   ```

### 7. File Transfer Failed

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

## Diagnostic Commands

### Server Diagnostics
```bash
# System info
uname -a
cat /etc/os-release

# Network
ip addr
ip route
ss -tuln

# Resources
df -h
free -h
uptime
top -bn1 | head -15

# Process
ps aux | head -20
ps -ef | grep ssh

# Logs
tail -f /var/log/secure
journalctl -u sshd -n 100
```

### MCP Diagnostics
```python
# Test password parsing
import json
password = "P/[KY}+wa7?2|uc"
print(json.dumps({"password": password}))
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
# Stop SSH
sudo systemctl stop sshd

# Kill stuck sessions
pkill -9 sshd

# Clear SSH sockets
rm -rf /run/sshd*

# Start SSH
sudo systemctl start sshd

# Check status
sudo systemctl status sshd
```

## Log Locations

| Service | Log Location |
|---------|-------------|
| SSH | `/var/log/secure` (RHEL/CentOS) |
| SSH | `/var/log/auth.log` (Debian/Ubuntu) |
| Docker | `journalctl -u docker` |
| System | `/var/log/messages` |

## Get Help

### Collect Debug Info
```bash
# Save to file
script debug_session.log

# Run commands
uname -a
df -h
free -h
systemctl status sshd
netstat -tuln | grep 22

# Exit script
exit
```

### Report Issue
Include:
1. Error message
2. Server IP/hostname
3. OS version: `cat /etc/os-release`
4. SSH version: `ssh -V`
5. Relevant log excerpts

## Common Server Fixes

### Restart SSH Service
```bash
sudo systemctl restart sshd
```

### Check SSH Config
```bash
sudo sshd -t  # Test config
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
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Set:
PermitRootLogin yes
PasswordAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```
