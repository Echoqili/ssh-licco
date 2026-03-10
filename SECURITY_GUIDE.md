# SSH 安全配置指南

本文档介绍如何安全地配置 SSH 连接，避免密码泄露。

## 问题说明

在之前的实现中，密码会以明文形式显示在 MCP 工具调用日志中，这存在严重的安全风险。

## 解决方案

### 方案 1：使用环境变量（推荐）⭐

**步骤：**

1. **设置环境变量**
   
   Windows PowerShell:
   ```powershell
   $env:SSH_PASSWORD="你的密码"
   ```
   
   Windows CMD:
   ```cmd
   set SSH_PASSWORD=你的密码
   ```
   
   Linux/Mac:
   ```bash
   export SSH_PASSWORD="你的密码"
   ```

2. **配置 SSH 连接时不提供密码参数**

   ```json
   {
     "host": "43.143.207.242",
     "port": 22,
     "username": "root",
     "timeout": 120
   }
   ```

3. **系统会自动从环境变量读取密码**

**优点：**
- ✅ 密码不会出现在配置文件中
- ✅ 密码不会显示在工具调用日志中
- ✅ 每次会话临时设置，关闭终端后自动清除

### 方案 2：使用 SSH 密钥认证（最安全）🔐

**步骤：**

1. **生成 SSH 密钥对**
   
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519_mcp
   ```

2. **将公钥上传到服务器**
   
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519_mcp.pub root@43.143.207.242
   ```
   
   或手动复制：
   ```bash
   cat ~/.ssh/id_ed25519_mcp.pub | ssh root@43.143.207.242 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
   ```

3. **配置连接使用密钥认证**
   
   ```json
   {
     "host": "43.143.207.242",
     "port": 22,
     "username": "root",
     "private_key_path": "C:/Users/Administrator/.ssh/id_ed25519_mcp",
     "auth_method": "private_key"
   }
   ```

**优点：**
- ✅ 无需存储密码
- ✅ 更安全的认证方式
- ✅ 可设置密钥 passphrase 提供额外保护

### 方案 3：使用 Windows 凭据管理器

**步骤：**

1. **保存凭据到 Windows 凭据管理器**
   
   ```powershell
   cmdkey /target:SSH_43.143.207.242 /user:root /pass:"你的密码"
   ```

2. **在脚本中读取凭据**
   
   ```powershell
   $cred = cmdkey /list | Select-String "SSH_43.143.207.242"
   ```

## 配置文件安全建议

### 1. 设置文件权限

确保配置文件只有授权用户可以读取：

```powershell
# Windows - 使用 icacls
icacls "config\hosts.json" /inheritance:r /grant:r "%USERNAME%:R"

# Linux/Mac
chmod 600 config/hosts.json
```

### 2. 配置文件中不要存储密码

```json
{
  "ssh_hosts": [
    {
      "name": "我的服务器",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "",  // 留空，使用环境变量
      "timeout": 120,
      "banner_timeout": 120
    }
  ]
}
```

### 3. 使用 .gitignore 排除敏感文件

确保 `.gitignore` 包含：

```gitignore
# 配置文件（如果包含密码）
config/hosts.json
.ssh/mcp_config.json

# 密钥文件
*.pem
*.key
id_*
!id_*.pub

# 环境变量文件
.env
```

## 连接问题排查

### "Error reading SSH protocol banner" 错误

这通常由以下原因引起：

1. **网络延迟高** - 增加 `banner_timeout` 和 `timeout` 参数
   ```json
   {
     "timeout": 120,
     "banner_timeout": 120
   }
   ```

2. **SSH 服务器负载高** - 检查服务器状态
   ```bash
   # 检查 SSH 服务状态
   systemctl status sshd
   
   # 检查并发连接数
   netstat -an | grep :22 | wc -l
   ```

3. **防火墙限制** - 检查安全组规则
   - 确保端口 22 开放
   - 检查连接速率限制

4. **SSH 服务器配置** - 调整 `/etc/ssh/sshd_config`
   ```
   MaxStartups 100:30:200
   LoginGraceTime 120
   ```

## 最佳实践总结

1. ✅ **优先使用 SSH 密钥认证**
2. ✅ **使用环境变量存储密码**
3. ✅ **设置合理的超时时间**（特别是 banner_timeout）
4. ✅ **限制配置文件访问权限**
5. ✅ **定期更换密码和密钥**
6. ✅ **使用强密码策略**
7. ✅ **启用双因素认证（2FA）**
8. ✅ **监控 SSH 登录日志**

## 快速开始

```powershell
# 1. 设置环境变量
$env:SSH_PASSWORD="你的密码"

# 2. 配置连接（密码留空，自动从环境变量读取）
# 使用 ssh_config 工具，不提供 password 参数

# 3. 连接服务器
# 使用 ssh_login 工具

# 4. 验证连接
# 使用 ssh_execute 工具执行命令
```

## 需要帮助？

如果遇到问题，请检查：

1. 网络连接：`Test-NetConnection -ComputerName <host> -Port 22`
2. SSH 服务状态：`ssh -v root@<host>`
3. 环境变量：`echo $env:SSH_PASSWORD`（应显示密码）
4. 配置文件权限
