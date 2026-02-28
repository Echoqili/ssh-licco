# SSH LICCO 使用指南

## 目录

1. [功能简介](#功能简介)
2. [安装](#安装)
3. [在 Trae 中使用](#在-trae-中使用)
4. [在 Claude Desktop 中使用](#在-claude-desktop-中使用)
5. [工具说明](#工具说明)
6. [使用示例](#使用示例)
7. [配置文件说明](#配置文件说明)
8. [安全注意事项](#安全注意事项)
9. [发布到 MCP 市场](#发布到-mcp-市场)

---

## 功能简介

SSH LICCO 是一个基于 Model Context Protocol (MCP) 的服务器，让 AI 助手（如 Trae、Claude Desktop、Cursor）能够连接到远程 SSH 服务器执行命令。

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
git clone https://gitee.com/liccolicco/ssh-licco.git
cd ssh-licco
pip install -e .
```

### 验证安装

```bash
ssh-licco --help
```

---

## 在 Trae 中使用

### 步骤 1：配置 MCP

1. 打开 **Trae** 
2. 进入 **设置 (Settings)** → **MCP** 
3. 点击 **添加新服务器 (Add New Server)**
4. 填写配置：

```
名称: ssh
命令: ssh-licco
```

或者点击编辑配置文件，添加：

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

在 Trae 聊天中，直接使用以下命令：

#### 1. 配置 SSH 服务器（只需一次）

```
请配置 SSH 连接：
- 主机: 你的服务器IP
- 用户名: root
- 密码: 你的密码
```

或者使用工具调用：
```
调用 ssh_config，参数：{"host": "你的服务器IP", "username": "root", "password": "你的密码"}
```

#### 2. 登录并执行命令

```
登录 SSH 服务器，然后执行 "ls -la /home"
```

或者：
```
调用 ssh_login，参数：{"command": "whoami"}
```

#### 3. 保持会话执行多个命令

```
先登录 SSH，然后执行 "df -h" 查看磁盘，再执行 "free -h" 查看内存
```

---

## 在 Claude Desktop 中使用

### 步骤 1：找到配置文件

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 步骤 2：编辑配置

添加以下内容：

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

配置完成后，重启 Claude Desktop。

---

## 工具说明

### 1. ssh_config - 配置 SSH 服务器

配置 SSH 连接信息并保存到本地配置文件。

**参数：**

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| host | string | 127.0.0.1 | 否 | SSH 服务器 IP 或主机名 |
| port | number | 22 | 否 | SSH 端口 |
| username | string | root | 否 | SSH 用户名 |
| password | string | - | 是 | SSH 密码 |
| timeout | number | 30 | 否 | 连接超时（秒） |

**示例：**
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "root",
  "password": "your-password",
  "timeout": 30
}
```

---

### 2. ssh_login - 登录并执行命令

使用保存的配置登录 SSH 服务器，可选执行命令。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | 否 | 登录后执行的命令 |

**示例：**

```json
{
  "command": "ls -la /home"
}
```

---

### 3. ssh_connect - 直接连接

不依赖配置文件，直接使用完整参数连接 SSH。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| host | string | 是 | SSH 服务器 IP |
| port | number | 否 | SSH 端口 |
| username | string | 是 | SSH 用户名 |
| password | string | 否 | SSH 密码 |
| private_key_path | string | 否 | 私钥路径 |
| passphrase | string | 否 | 私钥密码 |
| auth_method | string | 否 | 认证方式：password/private_key/agent |

---

### 4. ssh_execute - 执行命令

在已连接的 SSH 会话中执行命令。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| command | string | 是 | 要执行的命令 |
| timeout | number | 否 | 超时时间（秒） |

---

### 5. ssh_disconnect - 断开连接

关闭指定的 SSH 会话。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 要关闭的会话 ID |

---

### 6. ssh_list_sessions - 列出会话

列出所有活跃的 SSH 会话。

**参数：** 无

---

### 7. ssh_generate_key - 生成密钥

生成 SSH 密钥对。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| key_type | string | ed25519 | 密钥类型：rsa/ed25519 |
| key_size | number | 4096 | RSA 密钥大小 |
| comment | string | - | 密钥注释 |
| save_path | string | - | 保存路径 |

---

## 使用示例

### 示例 1：查看服务器状态

**用户：**
```
查看服务器状态
```

**AI 调用：**
```
ssh_config: {"host": "你的服务器IP", "username": "root", "password": "你的密码"}
```

**AI 调用：**
```
ssh_login: {"command": "uptime && free -h && df -h"}
```

**返回：**
```
SSH登录成功!
主机: 你的服务器IP:22
Session ID: xxx
用户名: root
连接时间: xxx

--- 命令输出 ---
Exit Code: 0

 19:01:10 up 10 days, 7:07,  load average: 0.38, 0.37, 0.36
              total        used        free      shared  buff/cache   available
Mem:          1.7Gi       821Mi       285Mi       275Mi       614Mi       475Mi
Swap:            0B          0B          0B
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        50G  9.6G   38G  21% /
```

---

### 示例 2：管理文件

**用户：**
```
列出 /var/log 目录的内容
```

**AI 调用：**
```
ssh_login: {"command": "ls -la /var/log"}
```

---

### 示例 3：安装软件

**用户：**
```
在服务器上安装 nginx
```

**AI 调用：**
```
ssh_login: {"command": "apt-get update && apt-get install -y nginx"}
# 或者
ssh_login: {"command": "yum install -y nginx"}
```

---

### 示例 4：查看进程

**用户：**
```
查看服务器上正在运行的进程
```

**AI 调用：**
```
ssh_login: {"command": "ps aux | head -20"}
```

---

## 配置文件说明

### 保存位置

SSH 配置保存在：`~/.ssh/mcp_config.json`

### 配置文件格式

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

1. **密码安全**：密码本地存储，建议使用密钥认证
2. **不要泄露密码**：不要在公开场合分享服务器密码
3. **定期更换**：建议定期更换 SSH 密码或密钥
4. **限制权限**：尽量使用普通用户而非 root 用户
5. **防火墙**：配置防火墙规则，限制 SSH 访问来源
6. **敏感信息**：使用后及时清除配置文件中的密码

---

## 发布到 MCP 市场

### 前提条件

1. Gitee 账号（或 GitHub 账号）
2. 将代码推送到 Gitee 仓库

### 发布步骤

#### 1. 安装 Publisher CLI

**Windows PowerShell:**
```powershell
$arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "amd64" }
Invoke-WebRequest -Uri "https://github.com/modelcontextprotocol/registry/releases/download/v1.0.0/mcp-publisher_1.0.0_windows_$arch.tar.gz" -OutFile "mcp-publisher.tar.gz"
tar xf mcp-publisher.tar.gz mcp-publisher.exe
rm mcp-publisher.tar.gz
```

**macOS/Linux:**
```bash
brew install mcp-publisher
```

#### 2. 修改 server.json

编辑 `server.json`，将 `owner` 改为你的 Gitee 用户名：

```json
{
  "owner": "你的Gitee用户名",
  ...
}
```

#### 3. 发布

```bash
# 登录 GitHub（需要 GitHub 账号）
mcp-publisher login github

# 发布
mcp-publisher publish server.json
```

#### 4. 发布到 PyPI（可选）

```bash
pip install build twine
python -m build
twine upload dist/*
```

---

## 故障排除

### 连接失败

1. 检查服务器 IP 和端口是否正确
2. 确认用户名和密码正确
3. 检查服务器防火墙是否开放 SSH 端口
4. 确认网络连接正常

### 认证失败

1. 确认密码正确（注意特殊字符）
2. 尝试使用密钥认证
3. 检查服务器 SSH 配置

### 命令超时

1. 增加 timeout 参数值
2. 检查网络延迟
3. 确认命令本身没有卡住

---

## 技术支持

- 问题反馈：https://gitee.com/liccolicco/ssh-licco/issues
