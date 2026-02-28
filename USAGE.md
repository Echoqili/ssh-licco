# SSH LICCO 使用指南

## 简介

SSH LICCO 是一个基于 Model Context Protocol (MCP) 的服务器，让 AI 助手能够连接到远程 SSH 服务器执行命令。

### 核心功能

- ✅ SSH 密码认证登录
- ✅ 远程命令执行
- ✅ 多会话管理
- ✅ SSH 密钥生成
- ✅ SFTP 文件传输（开发中）

---

## 安装

### 方式一：pip 安装（推荐）

```bash
pip install ssh-licco
```

### 方式二：从源码安装

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e .
```

---

## 在 Trae 中使用

### 步骤 1：配置 MCP

1. 打开 **Trae**
2. 进入 **Settings** → **MCP**
3. 点击 **Add New Server**
4. 填写配置：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

### 步骤 2：重启 Trae

配置完成后，重启 Trae 使 MCP 服务器生效。

### 步骤 3：使用 SSH 功能

在 Trae 聊天中，直接说：

```
配置 SSH 连接：主机 43.143.207.242，用户名 root，密码 xxx
```

或者：

```
登录 SSH 服务器，然后执行 "ls -la /home"
```

---

## 在 Claude Desktop 中使用

### 步骤 1：找到配置文件

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 步骤 2：编辑配置

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

### 步骤 3：重启 Claude Desktop

---

## 工具说明

### 1. ssh_config - 配置 SSH 服务器

配置 SSH 连接信息并保存到本地。

**参数：**

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| host | string | 127.0.0.1 | 否 | SSH 服务器 IP |
| port | number | 22 | 否 | SSH 端口 |
| username | string | root | 否 | SSH 用户名 |
| password | string | - | 是 | SSH 密码 |
| timeout | number | 30 | 否 | 连接超时（秒） |

---

### 2. ssh_login - 登录并执行命令

使用保存的配置登录 SSH 服务器。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | 否 | 登录后执行的命令 |

---

### 3. ssh_connect - 直接连接

不依赖配置文件，直接连接 SSH。

---

### 4. ssh_execute - 执行命令

在已连接的 SSH 会话中执行命令。

---

### 5. ssh_disconnect - 断开连接

关闭 SSH 会话。

---

### 6. ssh_list_sessions - 列出会话

列出所有活跃的 SSH 会话。

---

### 7. ssh_generate_key - 生成密钥

生成 SSH 密钥对。

---

## 使用示例

### 示例 1：查看服务器状态

**你说：**
```
查看服务器状态
```

**AI 自动执行：**
```
1. ssh_config - 配置服务器
2. ssh_login - 登录并执行 "uptime && free -h && df -h"
```

---

### 示例 2：管理文件

**你说：**
```
列出 /var/log 目录的内容
```

---

### 示例 3：安装软件

**你说：**
```
在服务器上安装 nginx
```

---

## 配置文件

SSH 配置保存在：`~/.ssh/mcp_config.json`

```json
{
  "host": "你的服务器IP",
  "port": 22,
  "username": "root",
  "password": "你的密码",
  "timeout": 30
}
```

---

## 安全注意事项

⚠️ **重要提示：**

1. 密码本地存储，建议使用后清除配置文件
2. 不要在公开场合分享服务器密码
3. 定期更换 SSH 密码或使用密钥认证
4. 尽量使用普通用户而非 root 用户

---

## 故障排除

### 连接失败

1. 检查服务器 IP 和端口是否正确
2. 确认用户名和密码正确
3. 检查服务器防火墙是否开放 SSH 端口

### 认证失败

1. 确认密码正确（注意特殊字符）
2. 尝试使用密钥认证

---

## 技术支持

- 问题反馈：https://github.com/Echoqili/ssh-licco/issues
