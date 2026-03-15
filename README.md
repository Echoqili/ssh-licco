# 🚀 SSH LICCO

<!-- mcp-name: io.github.Echoqili/ssh-licco -->

[![PyPI version](https://badge.fury.io/py/ssh-licco.svg)](https://badge.fury.io/py/ssh-licco)
[![Python 3.10-3.13](https://img.shields.io/badge/python-3.10--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-green.svg)](https://registry.modelcontextprotocol.io/)

> **让 AI 帮你操作服务器！** 通过自然语言对话，AI 可以帮你执行命令、管理文件、查看日志、部署应用等。

---

## 📚 文档导航

### 快速开始
- **[⬇️ 安装指南](#-快速安装)** - 3 种安装方式
- **[🚀 快速开始](#-快速开始)** - 5 分钟上手
- **[📋 配置模板](#-完整配置示例)** - 开箱即用的配置

### 核心功能
- **[🔐 安全配置](#-安全配置)** - 多级安全策略
- **[🛠️ 可用工具](#-可用工具)** - 完整功能列表
- **[💡 使用示例](#-使用示例)** - 实际应用场景

### 高级主题
- **[📖 完整配置指南](MCP_CONFIG_GUIDE.md)** - 所有配置选项详解
- **[🔧 故障排除](docs/API_REFERENCE.md)** - 常见问题解决
- **[📊 API 参考](docs/API_REFERENCE.md)** - 详细 API 文档

### 开发资源
- **[🎓 Skills 文档](docs/skills/)** - 开发、运维、安装指南
- **[📦 发布指南](docs/skills/RELEASE_SKILL.md)** - 版本发布流程
- **[🐛 GitHub Issues](https://github.com/Echoqili/ssh-licco/issues)** - 问题反馈

---

## ✨ 特性亮点

- 🎯 **自然语言控制** - 用对话方式操作服务器
- 🔐 **多种认证方式** - 密码、密钥、Agent 转发
- 🔗 **长连接支持** - 自动保活（30 秒心跳），避免账户锁定
- ⏱️ **可配置超时** - Banner 超时 (60s)、会话超时 (2 小时)
- 📦 **异步高性能** - 基于 AsyncSSH 的异步架构
- 🛡️ **完善的异常处理** - 统一的错误处理机制
- 📊 **会话管理** - 支持多个并发 SSH 会话
- 📁 **SFTP 文件传输** - 上传、下载、目录管理
- 🔑 **密钥管理** - 生成和管理 SSH 密钥对
- 📝 **审计日志** - 完整的操作审计记录
- 🚀 **连接池** - 高性能连接复用
- 📊 **批量执行** - 多主机并行命令执行
- 🐳 **Docker 支持** - Docker 构建和状态监控
- 📋 **后台任务** - 异步任务执行和状态跟踪

---

## 📦 快速安装

### 方式一：pip 安装（推荐）

```bash
pip install ssh-licco
```

### 方式二：MCP 安装

```bash
mcp install io.github.Echoqili/ssh-licco
```

### 方式三：从源码安装

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e .
```

**Python 版本要求：** Python 3.10, 3.11, 3.12, 3.13

---

## 🚀 快速开始

### 1️⃣ 配置 MCP 服务器

#### 在 Trae / Cursor / Claude Desktop 中使用

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

### 2️⃣ 配置 SSH 连接（可选但推荐）

#### 方式 A：环境变量配置（推荐）

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_PORT": "22",
        "SSH_TIMEOUT": "60",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200",
        "SSH_CLIENT_TYPE": "common"
      }
    }
  }
}
```

**环境变量说明：**
- `SSH_HOST`: SSH 服务器地址
- `SSH_USER`: 用户名
- `SSH_PASSWORD`: 密码
- `SSH_PORT`: 端口（默认 22）
- `SSH_TIMEOUT`: 连接超时（秒）
- `SSH_KEEPALIVE_INTERVAL`: 保活间隔（秒）
- `SSH_SESSION_TIMEOUT`: 会话超时（秒）
- `SSH_CLIENT_TYPE`: SSH 客户端类型（可选，默认 `common`）
  - `common` - paramiko（稳定可靠，推荐）⭐
  - `performance` - asyncssh（高性能，适合高并发）🚀
  - `development` - fabric（简化 API，适合快速开发）👨‍💻

#### 方式 B：交互式配置

启动后，系统会提示输入连接信息：

```bash
python -m ssh_mcp.server
```

---

## 🔐 安全配置

> **重要**：从 v0.2.1 开始，ssh-licco 提供多级安全策略，可根据使用场景灵活配置。

### 多级安全策略

| 级别 | 名称 | 适用场景 | 安全评分 |
|------|------|----------|----------|
| **STRICT** | 严格模式 | 生产环境、公共服务器 | 最高 ⭐⭐⭐ |
| **BALANCED** | 平衡模式 | 开发环境、个人服务器（默认） | 高 ⭐⭐ |
| **RELAXED** | 宽松模式 | 测试环境、完全信任的服务器 | 中等 ⭐ |

### 快速配置

#### 方式 1：环境变量（推荐）

**Windows PowerShell**:
```powershell
$env:SSH_SECURITY_LEVEL = "balanced"
$env:SSH_EXTRA_ALLOWED_COMMANDS = "git,pip,npm"
python -m ssh_mcp.server
```

**Linux/Mac**:
```bash
export SSH_SECURITY_LEVEL="balanced"
export SSH_EXTRA_ALLOWED_COMMANDS="git,pip,npm"
python -m ssh_mcp.server
```

#### 方式 2：MCP 配置文件

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "git,pip,npm",
        "SSH_BASE_DIR": "/home"
      }
    }
  }
}
```

### 📖 详细文档

- **[MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md)** - 完整配置指南，包含 5 种使用场景示例
- **[SECURITY_CONFIG_GUIDE.md](SECURITY_CONFIG_GUIDE.md)** - 安全配置详解

---

## 🛠️ 可用工具

### SSH 连接管理

| 工具 | 描述 | 示例 |
|------|------|------|
| `ssh_connect` | 建立 SSH 连接 | 连接服务器 |
| `ssh_disconnect` | 断开 SSH 连接 | 释放连接资源 |
| `ssh_list_sessions` | 查看活动会话 | 管理多个连接 |

### 命令执行

| 工具 | 描述 | 示例 |
|------|------|------|
| `ssh_execute` | 执行 SSH 命令 | `ls -la`, `docker ps` |
| `ssh_background_task` | 后台任务执行 | Docker 构建、长时间运行任务 |
| `ssh_task_status` | 查看后台任务状态 | 检查任务进度 |

### 文件管理

| 工具 | 描述 | 示例 |
|------|------|------|
| `ssh_upload_file` | 上传文件 | 部署代码 |
| `ssh_download_file` | 下载文件 | 获取日志 |
| `ssh_list_directory` | 列出目录内容 | 查看文件结构 |

### 系统管理

| 工具 | 描述 | 示例 |
|------|------|------|
| `ssh_get_info` | 获取系统信息 | CPU、内存、磁盘 |
| `ssh_check_service` | 检查服务状态 | PostgreSQL、Nginx |
| `ssh_docker_build` | Docker 构建 | 构建镜像 |
| `ssh_docker_status` | Docker 状态 | 容器状态 |

### 📖 详细文档

- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - 完整 API 参考
- **[docs/skills/ssh-mcp-ops/SKILL.md](docs/skills/ssh-mcp-ops/SKILL.md)** - 运维操作指南

---

## 💡 使用示例

### 示例 1：执行命令

```
用户：帮我查看服务器上的 Docker 容器
AI：正在执行 `docker ps` 命令...

[执行结果]
CONTAINER ID   IMAGE     COMMAND   STATUS    PORTS
abc123         nginx     "nginx"   Up 2 days 80:80
```

### 示例 2：文件上传

```
用户：把这个文件上传到 /var/www/html
AI：正在上传文件到 /var/www/html...

[上传成功]
本地：./index.html
远程：/var/www/html/index.html
大小：2.3 KB
```

### 示例 3：后台任务

```
用户：帮我构建 Docker 镜像
AI：正在启动后台任务执行 `docker build -t myapp .`...

[任务启动]
Task ID: a1b2c3d4
命令：docker build -t myapp .
日志：/tmp/background_task.log

使用 ssh_task_status 查看进度
```

### 示例 4：数据库检查

```
用户：检查 PostgreSQL 是否正常运行
AI：正在执行 `pg_isready -h localhost -p 5432`...

[检查结果]
localhost:5432 - accepting connections
✅ PostgreSQL 运行正常
```

### 📖 更多示例

- **[docs/skills/ssh-mcp-ops/SKILL.md](docs/skills/ssh-mcp-ops/SKILL.md)** - 运维操作示例
- **[docs/skills/ssh-mcp-dev/SKILL.md](docs/skills/ssh-mcp-dev/SKILL.md)** - 开发场景示例

---

## 📋 完整配置示例

### 场景 1：Web 开发者

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "git,npm,docker,composer,pm2",
        "SSH_BASE_DIR": "/var/www",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "deploy",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

### 场景 2：Python 开发者

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "pip,poetry,python3,pytest,black",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "developer",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

### 场景 3：数据库管理员

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "psql,mysql,mongosh,pg_isready",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "dbadmin",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

### 场景 4：系统管理员

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "relaxed",
        "SSH_EXTRA_ALLOWED_COMMANDS": "sudo,apt,yum,systemctl,journalctl,docker,kubectl",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

### 场景 5：生产环境（最高安全）

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "strict",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "app-user",
        "SSH_PASSWORD": "your-password",
        "SSH_BASE_DIR": "/home/app-user"
      }
    }
  }
}
```

### 📖 更多配置

- **[MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md)** - 包含所有配置选项的详细说明

---

## 🔧 故障排查

### 常见问题

#### 1. 连接失败

**错误**: `Connection refused`

**解决**:
- 检查 SSH 服务是否运行：`systemctl status sshd`
- 检查防火墙设置：`ufw status`
- 确认端口正确：默认 22

#### 2. 认证失败

**错误**: `Authentication failed`

**解决**:
- 检查用户名和密码
- 尝试使用密钥认证
- 查看 SSH 日志：`/var/log/auth.log`

#### 3. 命令被阻止

**错误**: `命令 'xxx' 不在允许列表中`

**解决**:
```json
{
  "SSH_SECURITY_LEVEL": "balanced",
  "SSH_EXTRA_ALLOWED_COMMANDS": "被阻止的命令"
}
```

#### 4. 后台任务失败

**错误**: `'SSHMCPServer' object has no attribute '_logger'`

**解决**: 升级到最新版本 v0.2.3+
```bash
pip install --upgrade ssh-licco
```

### 📖 详细文档

- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - API 参考和错误处理
- **[docs/skills/ssh-mcp-troubleshoot/SKILL.md](docs/skills/ssh-mcp-troubleshoot/SKILL.md)** - 故障排除指南
- **[MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md)** - 配置故障排查

---

## 🎓 学习资源

### Skills 文档

- **[📦 发布指南](docs/skills/RELEASE_SKILL.md)** - 完整的版本发布流程
- **[🔧 开发指南](docs/skills/ssh-mcp-dev/SKILL.md)** - 开发环境和流程
- **[🛠️ 运维指南](docs/skills/ssh-mcp-ops/SKILL.md)** - 运维操作最佳实践
- **[⚙️ 安装指南](docs/skills/ssh-mcp-setup/SKILL.md)** - 安装和配置步骤
- **[🔍 故障排除](docs/skills/ssh-mcp-troubleshoot/SKILL.md)** - 常见问题解决

### 配置文档

- **[MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md)** - 完整配置指南
- **[SECURITY_CONFIG_GUIDE.md](SECURITY_CONFIG_GUIDE.md)** - 安全配置详解

### API 文档

- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - API 参考文档

---

## 🔗 相关链接

### 项目资源

- **GitHub**: https://github.com/Echoqili/ssh-licco
- **PyPI**: https://pypi.org/project/ssh-licco/
- **MCP Registry**: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco
- **Issues**: https://github.com/Echoqili/ssh-licco/issues

### 文档索引

| 文档 | 描述 | 位置 |
|------|------|------|
| 📖 配置指南 | 完整配置选项和场景 | [MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md) |
| 🔐 安全指南 | 安全配置详解 | [SECURITY_CONFIG_GUIDE.md](SECURITY_CONFIG_GUIDE.md) |
| 📊 API 参考 | 完整 API 文档 | [docs/API_REFERENCE.md](docs/API_REFERENCE.md) |
| 🎓 Skills | 开发、运维、安装指南 | [docs/skills/](docs/skills/) |
| 📦 发布指南 | 版本发布流程 | [docs/skills/RELEASE_SKILL.md](docs/skills/RELEASE_SKILL.md) |

---

## 📊 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.2.3 | 2026-03-14 | 修复 `_logger` 初始化 bug |
| v0.2.2 | 2026-03-14 | 安全配置增强（有 bug） |
| v0.2.1 | 2026-03-13 | 多级安全策略、环境变量配置 |
| v0.2.0 | 2026-03-12 | 安全验证模块、命令白名单 |
| v0.1.7 | 2026-03-11 | 基础功能、后台任务 |

---

## 🤝 贡献指南

欢迎贡献代码、文档和建议！

### 开发流程

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

### 开发资源

- **[docs/skills/ssh-mcp-dev/SKILL.md](docs/skills/ssh-mcp-dev/SKILL.md)** - 开发指南
- **[docs/skills/RELEASE_SKILL.md](docs/skills/RELEASE_SKILL.md)** - 发布流程

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 💬 获取帮助

### 遇到问题？

1. **查看文档**: [MCP_CONFIG_GUIDE.md](MCP_CONFIG_GUIDE.md)
2. **故障排除**: [docs/skills/ssh-mcp-troubleshoot/SKILL.md](docs/skills/ssh-mcp-troubleshoot/SKILL.md)
3. **提交 Issue**: [GitHub Issues](https://github.com/Echoqili/ssh-licco/issues)

### 社区支持

- GitHub Discussions
- MCP Community
- Stack Overflow (tag: `ssh-licco`)

---

**Made with ❤️ by Echoqili**

*Last updated: 2026-03-14*
