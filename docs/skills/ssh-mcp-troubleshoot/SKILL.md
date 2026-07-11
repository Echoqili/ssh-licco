---
name: "ssh-mcp-troubleshoot"
description: "SSH MCP troubleshooting guide. Invoke when user encounters connection issues, authentication errors, npm/npx startup problems, or needs to diagnose SSH/Docker problems."
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

**Method 3: 加固点 3（`SSH_REMOTE_GUARD=true`）会拒绝元字符**

如确需复杂命令：
- 在配置 `SSH_EXTRA_ALLOWED_COMMANDS` 之外，**不要**继续尝试向 env 加 `SSH_EXTRA_ALLOWED_PATTERNS`——该变量不存在（v2.3.0 之前是 phantom）
- 在跳板机本地拆分为多条简单命令分别执行
- 或关闭 `SSH_REMOTE_GUARD`（生产不推荐）

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

### 8. Docker Build Failed — 分层排查指南

当本地运行 `docker build` 失败时，先看返回信息定位故障层，再针对性解决。

#### 8.1 定位故障层

根据返回信息判断问题出在哪一层：

| 返回特征 | 故障层 | 排查方向 |
|----------|--------|----------|
| `Background task failed to start! PID=DEAD` | 环境配置 | Docker 守护进程/磁盘/内存 |
| `Background Task Started! PID=xxx STATUS=RUNNING` 但最终失败 | 代码逻辑 | Dockerfile 或 build 参数 |
| `Security error: 命令 'xxx' 不在允许列表中` | 安全白名单 | `SSH_SECURITY_LEVEL` / `SSH_EXTRA_ALLOWED_COMMANDS` |
| `Command blocked by security policy` | 安全策略 | 命令含有 `\|` `;` 等危险字符 |

#### 8.2 环境配置排查（现象：PID=DEAD）

`_execute_background`（server.py#L574）后台启动机制：
1. `nohup bash -c 'docker build ...'` 启动 build
2. `sleep 1` 等进程跑起来
3. `ps -p $PID` 检查进程存活

**PID=DEAD 意味着进程启动后 1 秒内被杀**，常见原因：

```bash
# 1. Docker 守护进程未运行
sudo systemctl status docker
sudo systemctl start docker

# 2. 磁盘空间满
df -h

# 3. 内存不足
free -h

# 4. Docker 权限问题（当前用户不在 docker 组）
sudo usermod -aG docker $USER
# 退出重新登录后生效

# 5. Docker socket 权限
ls -la /var/run/docker.sock

# 6. 直接前台跑一次（看真实错误）
docker build -t test:latest .
```

#### 8.3 代码逻辑排查（现象：PID=RUNNING 但 build 失败）

后台机制正常，问题出在 Dockerfile 或 build 参数：

```bash
# 查看 build 日志
ssh_execute command="cat /tmp/docker_build_xxxx.log"

# 看最后 50 行（通常错误在末尾）
ssh_execute command="tail -50 /tmp/docker_build_xxxx.log"

# 手动前台重跑验证
docker build -t test:latest -f ./Dockerfile .
```

常见 Dockerfile 问题：
- 基础镜像不存在或无法拉取（网络/镜像源）
- Dockerfile 语法错误
- COPY/ADD 的源路径不存在
- RUN 命令返回非零退出码
- 缓存冲突（尝试 `--no-cache`）

#### 8.4 快速诊断命令

一次性排查所有环境问题：

```bash
ssh_execute command="echo '=== DOCKER INFO ===' && docker info 2>&1 | grep -E 'Server Version|Storage Driver|Docker Root Dir' && echo '=== DISK ===' && df -h / && echo '=== MEM ===' && free -h && echo '=== DOCKERFILE ===' && test -f ./Dockerfile && echo 'OK' || echo 'MISSING'"
```

#### 8.5 一键诊断矩阵

| 输出特征 | 前台 `docker build` 结果 | 结论 |
|----------|-------------------------|------|
| `PID=DEAD` | 成功 ✅ | 后台机制问题（`_execute_background`） |
| `PID=DEAD` | 也失败 ❌ | 环境问题（Docker 未运行/磁盘满/权限） |
| `PID=RUNNING` | 成功 ✅ | Dockerfile 或 build 参数问题 |
| `PID=RUNNING` | 也失败 ❌ | 并发问题（资源竞争、锁冲突） |
| 安全错误 | 同上 | 安全白名单配置问题 |

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
- `ssh_host` shows password conflict warning
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

### 12. npx `Cannot find module` Error (Startup Failure)

**Symptoms**:
- 配置 `"command": "npx", "args": ["ssh-licco"]` 后 MCP 客户端报错
- 错误包含 `Cannot find module '.../node_modules/ssh-licco/bin/ssh-licco.js'`
- 错误包含 `MODULE_NOT_FOUND`

**Cause**: npm 全局目录中存在损坏/不完整的 `ssh-licco` 包，导致 `npx` 加载本地缓存而非下载新包。

**Solution 1: Clean npm global package (recommended)**:
```bash
npm uninstall -g ssh-licco
```
卸载后 `npx ssh-licco` 会重新从 npm registry 下载完整包，自动安装 Python 依赖并运行。

**Solution 2: Use local source directly (for development)**:
如果本地有项目源码，将 MCP 配置改为直接引用本地文件：
```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "node",
      "args": ["D:\\path\\to\\ssh-licco\\ssh-licco.js"],
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        ...
      }
    }
  }
}
```

**Solution 3: Run smart installer directly**:
```bash
python smart_install.py
```

**Prevention**:
- 初次使用 `npx ssh-licco` 前，确保没有全局安装的损坏包
- 如果全局安装过旧版本，先 `npm uninstall -g ssh-licco` 清理
- 避免将全局 npm 缓存路径设置为项目源码路径

### 13. Anaconda `ModuleNotFoundError: No module named 'ssh_mcp'`

**Symptoms**:
- 错误栈指向 `D:\software\anaconda\Scripts\ssh-licco.exe\__main__.py`
- `ModuleNotFoundError: No module named 'ssh_mcp'`
- `pip show ssh-licco` 显示 `WARNING: Ignoring invalid distribution ~sh-licco`
- `where ssh-licco` 找不到命令，但 exe 文件实际存在

**Cause**: Anaconda 的 `site-packages` 目录中存在带 `~` 前缀的损坏残留目录（如 `~sh_licco-0.5.5.dist-info`），pip 的 `console_scripts` 入口点（`ssh-licco.exe`）存在但模块已丢失。通常由 pip 安装过程中断导致。

---

**Diagnosis Flow**（复现该问题的完整排查步骤）：

```powershell
# 1. 检查 pip 中包的状态
pip show ssh-licco
# → WARNING: Ignoring invalid distribution ~sh-licco
# → Package(s) not found: ssh-licco

# 2. 检查可执行文件
where ssh-licco
# → 可能找不到（PATH 未包含 Anaconda Scripts）
Get-ChildItem D:\software\anaconda\Scripts\ssh-licco*
# → ssh-licco.exe 存在（入口点残留）

# 3. 检查 site-packages 中的残留
Get-ChildItem D:\software\anaconda\Lib\site-packages | Where-Object { $_.Name -like "~*licco*" }
# → ~sh_licco-0.5.5.dist-info 目录（带 ~ 前缀 = pip 标记为损坏）

# 4. 尝试直接导入验证
D:\software\anaconda\python.exe -c "from ssh_mcp.cli import main; print('OK')"
# → ModuleNotFoundError: No module named 'ssh_mcp'

# 5. 尝试 pip 安装后再次验证
D:\software\anaconda\python.exe -m pip install --force-reinstall ssh-licco
# → 成功安装 0.5.4 及 33 个依赖
# → 仍报 WARNING: Ignoring invalid distribution ~sh-licco（~ 目录未清理）
```

---

**Fix: Diagnosis-based repair**:

```powershell
# Step 1: Clean corrupted ~-prefixed dist-info using Python（shell 权限限制时用）
D:\software\anaconda\python.exe -c "import shutil, os; path = r'D:\software\anaconda\Lib\site-packages'; [shutil.rmtree(os.path.join(path, d), ignore_errors=True) for d in os.listdir(path) if d.startswith('~') and 'licco' in d.lower()]"

# Step 2: Verify cleanup
D:\software\anaconda\python.exe -m pip show ssh-licco
# → WARNING 消失
# → Version: 0.5.4 (from PyPI)

# Step 3: Install local dev version (editable) to get latest code
D:\software\anaconda\python.exe -m pip install -e D:\pyworkplace\ssh-mcp
# → Successfully installed ssh-licco-0.5.5

# Step 4: Verify complete import chain
D:\software\anaconda\python.exe -c "from ssh_mcp.server import SSHMCPServer; from ssh_mcp.session_manager import SessionManager; from ssh_mcp.cli import main; print('OK')"
# → OK ✅
```

**Key Commands Quick Reference**:

| Purpose | Command |
|---------|---------|
| 检查包状态 | `pip show ssh-licco` |
| 检查可执行文件 | `Get-ChildItem <Anaconda>\Scripts\ssh-licco*` |
| 查找损坏残留 | `Get-ChildItem <Anaconda>\Lib\site-packages \| ? { $_.Name -like "~*licco*" }` |
| 一键清理残留 | `python -c "import shutil, os; ... shutil.rmtree(...)"` |
| 强制重装 | `<Anaconda>\python.exe -m pip install --force-reinstall ssh-licco` |
| 安装本地开发版 | `<Anaconda>\python.exe -m pip install -e D:\path\to\ssh-mcp` |
| 验证导入链 | `python -c "from ssh_mcp.server import SSHMCPServer; from ssh_mcp.session_manager import SessionManager; from ssh_mcp.cli import main; print('OK')"` |

**Prevention**:
- 如果要在 Anaconda 中使用，统一用 `D:\software\anaconda\python.exe -m pip install` 操作
- 不要在安装过程中中断 pip（可能导致 `~` 前缀的残留）
- ssh-licco 的 `npx` 方式使用独立 venv（`~/.ssh-licco-venv`），不受 Anaconda 环境影响
- 排查同类问题时，先走 `pip show → Get-ChildItem ~* → python.exe -c "import"` 三步诊断

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