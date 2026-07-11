# SSH-LICCO 生产加固方案（四项必做，v2.2.0 起第 4 项由"审批"改为"硬拦截"）

> 适用场景：SSH 跳板模式部署（无本地 CLI，AI 通过 MCP 调用 ssh-licco 代发命令到远端主机）
>
> 安全短板：跳板机是 SSH 代理的唯一执行点，一旦被突破即可对全部被管主机下发任意命令。
>
> 本文档对应代码实现见 `ssh_mcp/runtime_guard.py`、`ssh_mcp/secret_provider.py`、`ssh_mcp/security.py`（HARD_BLOCKED_PATTERNS）、`config/remote-guard/`。
> v2.1.0 引入的审批方案代码 `ssh_mcp/approval.py` 仍保留作为参考，但**生产不建议启用**。

---

## 加固点 1：运行账号最小权限

**目标**：跳板机不使用 root 启动 ssh-licco 进程，专用普通运维账号运行，禁止 sudo 权限。

**为什么**：跳板机进程权限 = 可下发的最大远端命令权限上限。root/sudo 启动会让命令白名单形同虚设——白名单内的任何命令都能以 root 身份在跳板机本地造成破坏（读取本地私钥、改 hosts.json、注入 sudo_password）。

### 实现

- 模块：`ssh_mcp/runtime_guard.py`
- 入口：`server.run_server()` 启动时调用 `enforce_runtime_guard()`
- 校验内容：
  1. 拒绝 root 启动（`os.geteuid() == 0`）
  2. 检测 `SUDO_*` / `PKEXEC_*` / `DOAS_*` 环境变量，拒绝 sudo 上下文启动
  3. 可选用户白名单（`SSH_RUNTIME_ALLOWED_USERS=sshlicco,ops`）

### 启用方式

```bash
# /etc/systemd/system/ssh-licco.service
[Service]
User=sshlicco                    # 专用普通账号
Group=sshlicco
# 禁止该账号 sudo（/etc/sudoers 或 /etc/sudoers.d/sshlicco）
# sshlicco ALL=(ALL) NOPASSWD:ALL  ← 绝对不要这样配
ExecStart=/usr/bin/python -m ssh_mcp
Environment=SSH_RUNTIME_GUARD=true
Environment=SSH_RUNTIME_ALLOWED_USERS=sshlicco
```

```bash
# 创建专用账号（无 sudo 权限）
useradd -r -m -d /home/sshlicco -s /usr/sbin/nologin sshlicco
# sudoers 中显式不给 sshlicco 任何 sudo 权限（默认就没有，确认即可）
```

### 验证

```bash
# 用 root 启动应被拒绝
sudo systemctl start ssh-licco  # 退出码 2，日志见 "ssh-licco 进程以 root 身份启动被拒绝"

# 用 sshlicco 账号启动正常
sudo -u sshlicco systemctl start ssh-licco
```

---

## 加固点 2：密钥不落地磁盘

**目标**：服务器私钥托管到密钥管理服务（KMS/Vault），跳板机只临时调取凭证到内存，不持久保存私钥文件。

**为什么**：私钥落盘 = 私钥泄露面。跳板机磁盘被攻破、被备份、被取证都会导致私钥外泄，进而整个被管主机群沦陷。

### 实现

- 模块：`ssh_mcp/secret_provider.py`（SecretManager + env/command/http 三种 provider）
- 模块：`ssh_mcp/key_manager.py` 新增 `load_key_from_str()`（内存加载私钥，不接触磁盘）
- `KeyManager.save_key()` 在「密钥不落地」模式启用时抛 `PermissionError`，强制走内存路径
- `ConnectionConfig` 新增 `private_key_material` 字段（内存私钥 PEM）
- `paramiko_client` / `session_manager` 优先使用内存私钥（`pkey=` 参数），而非 `key_filename=`
- `_handle_connect` 在 SecretManager 启用时自动从 KMS 拉取私钥到内存，连接建立后立即 `release()` 清零

### 启用方式

```bash
# 方式 A：env provider（开发/CI 用，私钥从环境变量注入，仍不落盘）
Environment=SSH_SECRET_PROVIDER_ENABLED=true
Environment=SSH_SECRET_PROVIDER=env
Environment=SSH_SECRET_ENV_KEY_PROD_DB=-----BEGIN OPENSSH PRIVATE KEY-----\n...

# 方式 B：command provider（生产推荐，从 Vault/KMS 拉取）
Environment=SSH_SECRET_PROVIDER_ENABLED=true
Environment=SSH_SECRET_PROVIDER=command
Environment=SSH_SECRET_COMMAND_PROD_DB=vault kv get -field=private_key secret/ssh/prod-db

# 方式 C：http provider（从内部 KMS HTTP 接口拉取）
Environment=SSH_SECRET_PROVIDER_ENABLED=true
Environment=SSH_SECRET_PROVIDER=http
Environment=SSH_SECRET_HTTP_TOKEN=<service-token>
Environment=SSH_SECRET_HTTP_URL_PROD_DB=https://kms.internal/ssh-keys/prod-db
```

> 私钥内容仅存活于进程内存，`SecretMaterial.wipe()` 用 `bytearray` 逐字节清零；进程退出时 `atexit` 钩子统一清理所有未释放凭证。

### 验证

```bash
# 启用后尝试用 private_key_path 连接应被拒绝
# （MCP 返回："密钥不落地模式已启用...禁止使用 private_key_path 指定磁盘私钥文件"）

# 确认跳板机磁盘无私钥文件
find /home/sshlicco -name "id_*" -o -name "*.pem" 2>/dev/null  # 应无输出
```

---

## 加固点 3：双层命令拦截

**目标**：跳板机 ssh-licco 侧完成第一层命令白名单过滤；远端主机配置 ForceCommand 做二次命令校验，防止 SSH 逃逸绕过管控。

**为什么**：单层白名单可被 shell 元字符绕过——例如 `ls; rm -rf /`，跳板机侧白名单只看第一个 token `ls` 放行，但远端 bash 执行时会跑两条命令。双层拦截 + 命令规范化可关闭此逃逸路径。

### 实现

**第一层（跳板机 ssh-licco 侧）**：
- `server._normalize_command_for_remote_guard()`：当 `remote_guard=True` 或 `SSH_REMOTE_GUARD=true` 时，强制命令为单一 argv 形式，禁止 `| ; & $() \` > < && ||` 等元字符
- 已有的 `CommandValidator` 白名单/黑名单继续生效

**第二层（远端被管主机侧）**：
- `config/remote-guard/ssh_licco_force_command.sh`：部署到远端 `/usr/local/bin/`，作为 sshd 的 ForceCommand
- `config/remote-guard/allowed_commands.txt`：远端白名单，部署到 `/etc/ssh_licco/`
- `config/remote-guard/sshd_config.example`：sshd_config Match User 片段

### 部署步骤（远端每台被管主机）

```bash
# 1. 拷贝脚本和白名单
scp config/remote-guard/ssh_licco_force_command.sh root@host:/usr/local/bin/
scp config/remote-guard/allowed_commands.txt root@host:/etc/ssh_licco/
ssh root@host "chmod +x /usr/local/bin/ssh_licco_force_command.sh"
ssh root@host "mkdir -p /etc/ssh_licco && touch /var/log/ssh_licco_force_command.log"

# 2. 创建专用账号（每个被管主机一个）
ssh root@host "useradd -m -s /bin/bash sshlicco"
# 把跳板机的公钥放进 sshlicco 的 authorized_keys

# 3. 配置 sshd ForceCommand（追加到 /etc/ssh/sshd_config 或放入 sshd_config.d/）
# 参见 config/remote-guard/sshd_config.example
ssh root@host "cat >> /etc/ssh/sshd_config <<'EOF'
Match User sshlicco
    ForceCommand /usr/local/bin/ssh_licco_force_command.sh
    AllowTcpForwarding no
    X11Forwarding no
    PermitTunnel no
    AllowAgentForwarding no
    PasswordAuthentication no
    AllowUsers sshlicco@<跳板机IP>
EOF
systemctl restart sshd"
```

### 启用第一层（跳板机 ssh-licco 侧）

```bash
# 全局开启命令规范化
Environment=SSH_REMOTE_GUARD=true

# 或按需在 ssh_execute 调用时指定
# ssh_execute(command="ls -la", remote_guard=true)
```

### 验证

```bash
# 跳板机侧：含管道的命令被第一层拦截
# ssh_execute(command="ls | grep foo", remote_guard=true)
# → "❌ 命令被远端 guard 模式拦截（第一层）...禁止 shell 元字符"

# 远端侧：未在白名单的命令被第二层拦截
# 审计日志 /var/log/ssh_licco_force_command.log
# 2026-06-29 22:00:00 | DENY_NOT_IN_WHITELIST | user=sshlicco | cmd=wget ...
```

---

## 加固点 4：灾难性命令硬拦截（v2.2.0 起，原"高危操作审批"被取代）

**目标**：rm -rf 绝对路径、mkfs、raw-disk dd、fork-bomb、root chmod 等灾难性命令在 MCP 网关层被**无条件**拒绝，AI 不能直接下发，也无任何参数可绕过。

**为什么**：v2.1.0 的"高危操作审批"方案依赖 AI 自报命令 + 运维人员背书，存在闭环风险（AI 完全可以绕过审批直接构造一个看似无害的命令）。v2.2.0 改为硬拦截——直接以"任何安全级别、任何参数都不能绕过"的方式拒绝灾难性模式，更安全也更简单。

### 实现

- 模块：`ssh_mcp/security.py::CommandValidator.HARD_BLOCKED_PATTERNS` + `CommandValidator.check_hard_block()`
- 工作流：
  ```
  AI ssh_execute(command="rm -rf /etc")
       ↓
  check_hard_block() 在所有其他校验之前先执行
       ↓
  匹配 → SecurityError(hard_block=True) → WARNING 审计日志 → 返回 ❌ 硬拦截错误
  ```
- 拦截模式（不依赖任何配置，无开关）：
  - `rm -rf` 作用于绝对路径（含 `/`、`/*`、`/path`、`/path/*`，`-fr` 变体同效）
  - `mkfs.*` 任意文件系统格式化
  - `dd if=/dev/(zero|random|urandom) of=/dev/(sd|nvme)` 覆写裸盘
  - bash fork-bomb（`:(){ :|:& };:` 及空白变体）
  - `chmod -R 777 /` / `chmod -R 000 /` 根目录递归改权限
  - `> /dev/(sd|nvme)` / `>> /dev/(sd|nvme)` 裸设备重定向

### 安全特性

- **零配置**：默认开启，无环境变量开关
- **零绕过**：`SSH_SECURITY_LEVEL`、`confirm_dangerous=true`、`confirmation_layer=N` 等任何参数均无效
- **审计日志**：命中时输出 `WARNING` 日志（含 `category` 与命令原文），便于 SOC 监控
- **错误信息明确**：不暗示任何 bypass 路径，直接指向"请直接登录服务器操作"

### 验证

```python
from ssh_mcp.security import CommandValidator, SecurityError, SecurityLevel

# 1. 绝对路径 rm -rf 应被硬拦截
v = CommandValidator(security_level=SecurityLevel.BALANCED)
try:
    v.validate_command("rm -rf /etc")
    assert False, "should be blocked"
except SecurityError as e:
    assert e.hard_block is True

# 2. mkfs 应被硬拦截
try:
    v.check_hard_block("mkfs.ext4 /dev/sda1")
    assert False
except SecurityError as e:
    assert e.hard_block is True

# 3. 相对路径 rm -rf 不被硬拦截（仍走软门）
v.check_hard_block("rm -rf ./build/")  # 不抛异常

# 4. 单文件 rm 不被拦截
v.check_hard_block("rm /tmp/test.log")  # 不抛异常
```

### v2.1.0 的审批方案（已下线，仅作历史参考）

- 旧模块：`ssh_mcp/approval.py`（ApprovalGate 单例，JSON 持久化）
- 旧工作流：
  ```
  AI ssh_execute(高危命令) → 审批门禁拦截（无 approval_id）
       ↓
  AI ssh_request_approval(command, reason) → 生成 approval_id，status=pending
       ↓
  运维人员 ssh_approve_command(approval_id, decision=approved, reviewer=...)
       ↓
  AI ssh_execute(command, approval_id) → 门禁校验通过，执行（一次性消费）
  ```
- 旧 MCP 工具（已从 `list_tools()` 移除）：
  - `ssh_request_approval`
  - `ssh_approve_command`
  - `ssh_list_approvals`
- 旧 `ssh_execute` 参数：`approval_id`（v2.2.0 起已从 inputSchema 移除）
- 旧代码保留：`ssh_mcp/approval.py`、`ssh_mcp/handlers/approval.py` 仍存在，作为参考实现；不建议在生产启用 `SSH_APPROVAL_GATE=true`

---

## 环境变量速查

| 变量 | 默认 | 说明 |
|------|------|------|
| `SSH_RUNTIME_GUARD` | `false` | 加固点 1 总开关，生产置 `true` |
| `SSH_RUNTIME_ALLOW_ROOT` | `false` | 是否允许 root 启动（不推荐开） |
| `SSH_RUNTIME_ALLOWED_USERS` | (空) | 允许启动的账号白名单，逗号分隔 |
| `SSH_RUNTIME_BLOCK_SUDO` | `true` | 是否拦截 sudo 上下文启动 |
| `SSH_SECRET_PROVIDER_ENABLED` | `false` | 加固点 2 总开关 |
| `SSH_SECRET_PROVIDER` | `env` | 凭证 provider：`env`/`command`/`http` |
| `SSH_SECRET_ENV_KEY_<NAME>` | — | env provider：连接 `<NAME>` 的私钥环境变量 |
| `SSH_SECRET_COMMAND_<NAME>` | — | command provider：拉取 `<NAME>` 私钥的命令 |
| `SSH_SECRET_HTTP_URL_<NAME>` | — | http provider：拉取 `<NAME>` 私钥的 URL |
| `SSH_SECRET_HTTP_TOKEN` | — | http provider：Bearer token |
| `SSH_REMOTE_GUARD` | `false` | 加固点 3 第一层总开关 |
| `SSH_APPROVAL_GATE` | `false` | **已废弃（v2.2.0）**：原加固点 4 审批门禁总开关，工具已下线，配置仅作历史参考 |
| `SSH_APPROVAL_STORE` | `~/.ssh_licco/approvals.json` | **已废弃（v2.2.0）**：原审批记录持久化路径 |
| `SSH_APPROVAL_TTL` | `3600` | **已废弃（v2.2.0）**：原审批有效期（秒） |

---

## 生产部署 Checklist

- [ ] 加固点 1：创建 `sshlicco` 专用账号，sudoers 不授权，systemd `User=sshlicco`，`SSH_RUNTIME_GUARD=true`
- [ ] 加固点 2：选定 KMS provider（推荐 command + Vault），`SSH_SECRET_PROVIDER_ENABLED=true`，确认跳板机磁盘无私钥文件
- [ ] 加固点 3：每台被管主机部署 ForceCommand 脚本 + 白名单，配置 sshd `Match User sshlicco`，跳板机侧 `SSH_REMOTE_GUARD=true`
- [ ] 加固点 4（v2.2.0 起）：**灾难性命令硬拦截**默认开启，零配置、零绕过，无需额外设置。可执行 `python -c "from ssh_mcp.security import CommandValidator, SecurityLevel; CommandValidator(SecurityLevel.BALANCED).validate_command('rm -rf /etc')"` 验证
- [ ] ~~`SSH_APPROVAL_GATE=true`~~（v2.2.0 起已废弃，工具已下线，**不要在生产启用**）
- [ ] 跑 `python test_hardening.py` 确认四项加固逻辑通过
- [ ] 审计日志开启：`SSH_AUDIT_LOG_PATH=/var/log/ssh-licco/audit.log`
