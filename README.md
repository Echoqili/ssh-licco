# 🚀 SSH LICCO

[![PyPI version](https://badge.fury.io/py/ssh-licco.svg)](https://badge.fury.io/py/ssh-licco)
[![Python 3.10-3.13](https://img.shields.io/badge/python-3.10--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**让 AI 帮你操作服务器！**

SSH LICCO 是一个基于 Model Context Protocol (MCP) 的 SSH 服务器，让 AI 助手（Trae、Cursor、Claude Desktop 等）能够直接连接和管理你的 SSH 服务器。通过自然语言对话，AI 可以帮你执行命令、管理文件、查看日志、部署应用等。

## ✨ 核心特性

- 🎯 **自然语言控制** - 直接用对话方式操作服务器
- 🔐 **多种认证方式** - 支持密码、密钥、Agent 转发
- 🔗 **长连接支持** - 自动保活，避免频繁连接导致账户锁定
- 📦 **多客户端支持** - Paramiko、Fabric、AsyncSSH 可插拔
- 🛡️ **完善的异常处理** - 统一的异常体系和错误处理
- 📊 **会话管理** - 支持多个并发 SSH 会话
- 📁 **SFTP 文件传输** - 上传、下载、列出目录
- 🔑 **密钥管理** - 生成、保存和管理 SSH 密钥对
- 📝 **详细日志记录** - 支持多级日志和文件输出
- 🚀 **高性能异步** - 基于 asyncio 的异步架构

### 技术栈
- Python 3.10 - 3.13
- MCP SDK 1.0+
- AsyncSSH 2.17.0+
- Pydantic 2.0+
- asyncio 异步架构

## 📦 安装

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

### 开发环境安装

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e ".[dev]"
```

**Python 版本要求：**
- ✅ Python 3.10, 3.11, 3.12, 3.13
- ❌ Python 3.9 及以下版本不支持
- ❌ Python 3.14 及以上版本未测试

## 🚀 快速开始

### 1. 配置 MCP 服务器

#### 在 Trae / Cursor 中使用

打开设置 → MCP → 添加新服务器：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

#### 在 Claude Desktop 中使用

配置文件位置：
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

### 2. 配置 SSH 主机（可选但推荐）

#### 方式 1：使用配置文件

```bash
cp config/hosts.json.example config/hosts.json
```

编辑 `config/hosts.json`：

```json
{
  "ssh_hosts": [
    {
      "name": "生产服务器",
      "host": "192.168.1.100",
      "port": 22,
      "username": "root",
      "password": "your_password",
      "timeout": 30
    },
    {
      "name": "测试服务器",
      "host": "192.168.1.101",
      "port": 2222,
      "username": "admin",
      "password": "test123"
    }
  ]
}
```

#### 方式 2：直接在 MCP 配置中指定

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200",
        "SSH_CLIENT_TYPE": "asyncssh"
      }
    }
  }
}
```

### 3. 开始使用

重启 AI 应用后，直接用自然语言对话：

**示例 1：查看服务器状态**
```
帮我看看服务器的负载情况
```

**示例 2：执行命令**
```
在服务器上执行 docker ps 查看运行中的容器
```

**示例 3：管理文件**
```
列出 /var/log 目录下的所有文件
```

**示例 4：安装软件**
```
在服务器上安装 nginx
```

**示例 5：上传文件**
```
把本地的 config.yaml 上传到服务器的 /etc 目录
```

## 🔥 长连接功能（避免账户锁定）

频繁连接 SSH 服务器可能导致账户被锁定。SSH LICCO 默认启用长连接和自动保活：

- **自动保活**：每 30 秒发送心跳包，保持连接活跃
- **持久会话**：默认保持 2 小时，避免频繁重连
- **可配置**：根据需求调整保活间隔和会话时长

### 配置参数

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "43.143.207.242",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your-password",
        "SSH_KEEPALIVE_INTERVAL": "30",  // 保活间隔（秒）
        "SSH_SESSION_TIMEOUT": "7200"    // 会话超时（秒）
      }
    }
  }
}
```

详细配置说明见 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)

## 🛠️ 可用工具

| 工具 | 说明 | 示例 |
|------|------|------|
| `ssh_config` | 配置 SSH 连接信息 | 配置服务器地址、用户名、密码 |
| `ssh_login` | 使用保存的配置登录 | 登录后执行命令 |
| `ssh_connect` | 直接连接 SSH | 支持预配置主机或即时连接 |
| `ssh_execute` | 执行命令 | 在会话中执行任意命令 |
| `ssh_disconnect` | 断开连接 | 关闭指定会话 |
| `ssh_list_sessions` | 列出活跃会话 | 查看所有 SSH 会话 |
| `ssh_generate_key` | 生成 SSH 密钥 | 创建 RSA 或 ED25519 密钥对 |
| `ssh_file_transfer` | SFTP 文件传输 | 上传、下载、列出目录 |

详细使用说明见 [USAGE.md](USAGE.md)

## 🏗️ 架构设计

SSH LICCO 采用分层架构设计，遵循最佳实践：

### 核心模块

```
ssh_mcp/
├── clients/              # SSH 客户端层（可插拔）
│   ├── interface.py     # 抽象接口定义
│   ├── paramiko_client.py  # Paramiko 实现
│   ├── additional_clients.py # 其他客户端实现
│   └── factory.py       # 客户端工厂
├── service.py           # 业务服务层
├── session_manager.py   # 会话管理
├── connection_config.py # 配置模型
├── exceptions.py        # 统一异常体系
├── logging_config.py    # 日志管理
└── server.py           # MCP 服务端
```

### 设计模式

- **工厂模式**：SSHClientFactory 动态创建客户端
- **策略模式**：支持多种 SSH 客户端实现
- **单例模式**：全局 SSHService 实例
- **上下文管理器**：自动连接/断开管理

### 客户端支持

当前仅支持 **AsyncSSH** 客户端：

| 客户端 | 类型 | 特点 | 安装 |
|--------|------|------|------|
| **AsyncSSH** | 异步 | 高并发性能，异步架构，默认且唯一 | `pip install asyncssh` |

**说明：** 为了简化维护和优化性能，本项目目前仅支持 AsyncSSH 客户端。AsyncSSH 提供：
- ✅ 异步架构，高并发性能
- ✅ 低资源占用
- ✅ 现代化的 API 设计
- ✅ 活跃的社区支持

### 配置客户端类型

当前默认且仅支持 **AsyncSSH** 客户端，无需额外配置。

如需指定（兼容性）：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_CLIENT_TYPE": "asyncssh"
      }
    }
  }
}
```

详见 [🔌 客户端类型配置指南](docs/CLIENT_TYPES.md)

## 🔒 安全注意事项

⚠️ **重要提示：**

1. **密码安全** - 密码仅本地存储，建议使用后清除配置文件
2. **不要分享** - 不要在公开场合分享服务器密码
3. **密钥认证** - 优先使用 SSH 密钥认证而非密码
4. **普通用户** - 尽量使用普通用户而非 root 用户
5. **文件权限** - 确保 `config/hosts.json` 文件权限设置为 600
6. **环境变量** - 使用环境变量存储敏感信息更安全

## 📚 文档

- [📖 使用指南](USAGE.md) - 详细的工具使用说明
- [⚙️ 配置指南](CONFIG_GUIDE.md) - 完整的配置选项说明
- [🐳 Docker 超时问题](DOCKER_MCP_TIMEOUT.md) - Docker 构建相关问题
- [📝 API 参考](docs/API_REFERENCE.md) - API 接口文档
- [❓ 故障排除](docs/TROUBLESHOOTING.md) - 常见问题和解决方案

## 💻 开发

### 运行测试

```bash
pytest
```

### 代码检查

```bash
# 代码格式化
ruff check ssh_mcp

# 类型检查
mypy ssh_mcp
```

### 构建文档

```bash
cd docs
mkdocs build
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

详见 [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [Paramiko](https://github.com/paramiko/paramiko) - SSH 库
- [Fabric](https://github.com/fabric/fabric) - 高级 SSH 库
- [AsyncSSH](https://github.com/ronf/asyncssh) - 异步 SSH 库

## 📬 联系方式

- **项目地址**: https://github.com/Echoqili/ssh-licco
- **问题反馈**: https://github.com/Echoqili/ssh-licco/issues
- **PyPI**: https://pypi.org/project/ssh-licco/

---

<div align="center">

**Made with ❤️ by SSH LICCO Team**

[![Star History Chart](https://api.star-history.com/svg?repos=Echoqili/ssh-licco&type=Date)](https://star-history.com/#Echoqili/ssh-licco&Date)

</div>
