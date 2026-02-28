# 🚀 SSH LICCO

让 AI 帮你操作服务器！

## 这是啥

SSH LICCO 是一个 MCP 服务器，连接 AI 助手和你的 SSH 服务器。有了它，你可以直接用自然语言让 AI 帮你操作服务器，比如：

- 🔍 查看服务器状态
- ⚡ 执行各种命令
- 📁 上传/下载文件
- 🔑 管理 SSH 密钥

## 快速安装

```bash
pip install ssh-licco
```

或者从源码安装：

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e .
```

## 快速开始

### 1. 配置 MCP

**Trae/Cursor:**
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

**Claude Desktop:**
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

配置文件位置：
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

### 2. 开搞！

重启你的 AI 应用，然后直接说：

```
帮我连接 192.168.1.100，用户名 root，密码 123456
```

或者：

```
看看服务器现在负载怎么样
```

## 配置 SSH 主机（推荐）

有两种方式配置服务器信息，不用每次都输入密码：

### 方式 1：使用独立配置文件（推荐）

复制示例文件并修改：
```bash
cp config/hosts.json.example config/hosts.json
```

然后编辑 `config/hosts.json`：
```json
{
  "ssh_hosts": [
    {
      "name": "我的服务器",
      "host": "192.168.1.100",
      "port": 22,
      "username": "root",
      "password": "your_password"
    }
  ]
}
```

### 方式 2：在 MCP 配置时直接指定

在 Trae 的 MCP 配置中添加环境变量：
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password"
      }
    }
  }
}
```

然后直接说：
```
连接"我的服务器"
```

> ⚠️ 提醒：`config/hosts.json` 已经加入 `.gitignore`，不会提交到 GitHub，放心用！

## 能干啥

| 工具 | 作用 |
|------|------|
| ssh_config | 配置 SSH 服务器 |
| ssh_login | 登录并执行命令 |
| ssh_connect | 直接连接 |
| ssh_execute | 执行命令 |
| ssh_disconnect | 断开连接 |
| ssh_list_sessions | 查看所有会话 |
| ssh_generate_key | 生成 SSH 密钥 |
| ssh_file_transfer | SFTP 文件传输 |

## 常见问题

**Q: 密码安全吗？**  
A: 密码只保存在本地 `~/.ssh/mcp_config.json`，不会发送到任何地方。

**Q: 能用密钥登录吗？**  
A: 可以！用 `ssh_connect` 时指定 `private_key_path` 参数即可。

**Q: 支持哪些 AI？**  
A: 支持所有支持 MCP 的 AI，比如 Trae、Claude Desktop、Cursor 等。

## 技术栈

- Python 3.10+
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Paramiko](https://github.com/paramiko/paramiko) - SSH 连接

## License

MIT
