# SSH LICCO 配置指南

## 📋 配置方式总览

SSH LICCO 支持多种配置方式，你可以根据需求选择：

1. **独立配置文件**（推荐）- `config/hosts.json`
2. **MCP 环境变量** - 在 MCP 配置中直接指定
3. **MCP 注册表配置** - `server.json`（用于发布）

---

## 方式 1：独立配置文件（推荐）

### 步骤

1. **复制示例文件**
   ```bash
   cp config/hosts.json.example config/hosts.json
   ```

2. **编辑配置文件**
   
   打开 `config/hosts.json`，填写你的服务器信息：
   ```json
   {
     "ssh_hosts": [
       {
         "name": "我的服务器",
         "host": "43.143.207.242",
         "port": 22,
         "username": "root",
         "password": "your-password",
         "timeout": 30
       },
       {
         "name": "测试服务器",
         "host": "192.168.1.100",
         "port": 2222,
         "username": "admin",
         "password": "test123",
         "timeout": 60
       }
     ]
   }
   ```

3. **在 Trae 中使用**
   ```
   连接"我的服务器"
   ```

### 优点
- ✅ 配置与管理分离
- ✅ 支持多个服务器
- ✅ 文件已加入 `.gitignore`，安全
- ✅ 易于版本控制（示例文件）

---

## 方式 2：MCP 环境变量配置

### 步骤

1. **编辑 Trae 的 MCP 配置**
   ```json
   {
     "mcpServers": {
       "ssh": {
         "command": "ssh-licco",
         "env": {
           "SSH_HOST": "43.143.207.242",
           "SSH_USER": "root",
           "SSH_PASSWORD": "your-password",
           "SSH_PORT": "22"
         }
       }
     }
   }
   ```

2. **在 Trae 中使用**
   ```
   连接服务器
   ```

### 优点
- ✅ 配置集中管理
- ✅ 适合单个服务器
- ⚠️ 密码在配置文件中，需注意安全

---

## 方式 3：server.json（MCP 注册表）

### 用途
用于发布到 MCP 官方注册表，不建议用于本地配置。

### 格式
```json
{
  "name": "io.github.Echoqili/ssh-licco",
  "description": "SSH MCP Server",
  "repository": {
    "url": "https://github.com/Echoqili/ssh-licco"
  },
  "packages": [...],
  "ssh_hosts": [
    {
      "name": "我的服务器",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "your-password"
    }
  ]
}
```

---

## 🔐 安全建议

### 1. 使用 SSH 密钥认证（推荐）

生成 SSH 密钥对：
```bash
ssh-keygen -t ed25519
```

配置中使用密钥路径：
```json
{
  "ssh_hosts": [
    {
      "name": "我的服务器",
      "host": "43.143.207.242",
      "username": "root",
      "private_key_path": "~/.ssh/id_ed25519"
    }
  ]
}
```

### 2. 文件权限设置

确保配置文件权限正确：
```bash
chmod 600 config/hosts.json
```

### 3. 不要提交密码

- `config/hosts.json` 已在 `.gitignore` 中
- 只提交 `config/hosts.json.example`（不含真实密码）

---

## 📊 配置优先级

系统按以下顺序查找配置：

1. **server.json** - 如果存在且包含 `ssh_hosts`
2. **config/hosts.json** - 推荐的本地配置方式
3. **MCP 环境变量** - 在 MCP 配置中指定
4. **~/.ssh/mcp_config.json** - 由 `ssh_config` 工具保存

---

## 🛠️ 配置管理命令

### 查看已配置的服务器
```bash
python -c "from ssh_mcp.config_manager import ConfigManager; cm = ConfigManager(); print(cm.list_hosts())"
```

### 测试连接
```bash
python test_connect.py
```

---

## 📝 配置参数说明

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| name | string | - | 是 | 服务器名称（用于识别） |
| host | string | - | 是 | 服务器 IP 或域名 |
| port | number | 22 | 否 | SSH 端口 |
| username | string | root | 否 | SSH 用户名 |
| password | string | - | 否 | SSH 密码（或使用密钥） |
| timeout | number | 30 | 否 | 连接超时（秒） |
| private_key_path | string | - | 否 | 私钥路径 |
| passphrase | string | - | 否 | 私钥密码 |

---

## ❓ 常见问题

### Q: 配置文件在哪里？
A: `config/hosts.json`（相对于项目根目录）

### Q: 可以配置多个服务器吗？
A: 可以！在 `ssh_hosts` 数组中添加多个配置即可

### Q: 如何切换服务器？
A: 在 Trae 中说 "连接 [服务器名称]" 即可

### Q: 密码安全吗？
A: 密码保存在本地文件，不会上传到 GitHub 或任何服务器

---

## 📚 更多信息

- [README.md](README.md) - 项目说明
- [USAGE.md](USAGE.md) - 详细使用指南
- [GitHub Issues](https://github.com/Echoqili/ssh-licco/issues) - 问题反馈
