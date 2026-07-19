# 🚀 SSH LICCO

<!-- mcp-name: io.github.Echoqili/ssh-licco -->

[![PyPI version](https://img.shields.io/pypi/v/ssh-licco.svg?cacheSeconds=1800)](https://pypi.org/project/ssh-licco/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-green.svg)](https://registry.modelcontextprotocol.io/)

> **让 AI 帮你操作服务器！** 通过自然语言对话，AI 可以帮你执行命令、管理文件、查看日志、部署应用等。

---

## 📚 文档导航

### 快速开始
- **[⬇️ 安装指南](#-快速安装)** - 2 种安装方式
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
- ⏱️ **可配置超时** - Banner 超时 (60s)、会话超时 (2 小时)，支持自动重连
- 📦 **异步高性能** - 基于 Paramiko 的异步架构（线程池 + asyncio）
- 🛡️ **完善的异常处理** - 统一的错误处理机制（7 层异常层次）
- 📊 **会话管理** - 支持多个并发 SSH 会话（最大 10 个，每主机 3 个）
- 📁 **SFTP 文件传输** - 上传、下载、目录管理
- 🖊️ **远程文件编辑** - 直接写入/追加文件内容，无需下载再上传
- 🔑 **密钥管理** - 生成和管理 SSH 密钥对（RSA/Ed25519）
- 📝 **审计日志** - 完整的操作审计记录（JSON 结构化日志）
- 🚀 **连接池** - 高性能连接复用（PooledConnection + ConnectionPool）
- 📊 **批量执行** - 多主机并行命令执行（BatchExecutor + AsyncBatchExecutor）
- 🐳 **Docker 支持** - Docker 构建和状态监控
- 📋 **后台任务** - 可靠的后台进程启动（nohup + bash -c 包装，单次 SSH 调用无竞态）
- 🖥️ **screen/tmux 会话** - 持久化远程会话，SSH 断开后进程依然存活
- 🪟 **Windows 服务器支持** - 支持 Windows Server（OpenSSH for Windows）与 Linux/macOS 目标主机
- 🔍 **进程管理** - 启动/停止/查询远程进程、SSH 端口转发（tunnel）
- 🔍 **看门狗** - 任务监控、心跳检测、全局异常处理
- 🛡️ **文件传输路径安全校验** - `ssh_file_transfer` delete 自动识别 Windows / Unix 路径风格并拦截敏感路径与路径遍历

---

## 🖥️ 目标主机支持

SSH-LICCO 基于标准 SSH/SFTP 协议，可连接以下目标主机：

| 操作系统 | 要求 | 备注 |
|---|---|---|
| **Linux** | OpenSSH 7.0+ | 推荐，完整支持所有功能 |
| **Windows Server** | OpenSSH for Windows / PowerShell Remoting over SSH | v2.1.3+ 支持 Windows 路径风格与安全校验 |
| **macOS** | 系统内置 OpenSSH | 完整支持 |

> **提示**：连接 Windows 服务器时，请使用 Windows 风格路径（如 `C:\temp\file.txt`），系统会自动识别并进行路径安全校验。

---

## 📦 快速安装

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

**Python 版本要求：** Python 3.10+

---

## 🚀 快速开始

### 1️⃣ 配置 MCP 服务器

#### 在 Trae / Cursor / Claude Desktop 中使用

打开设置 → MCP → 添加新服务器：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "python -m ssh_mcp.server"
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
      "command": "python -m ssh_mcp.server",
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
```

**Linux/Mac**:
```bash
export SSH_SECURITY_LEVEL="balanced"
export SSH_EXTRA_ALLOWED_COMMANDS="git,pip,npm"
```

#### 方式 2：MCP 配置文件

```json
{
  "mcpServers": {
    "ssh": {
      "command": "python -m ssh_mcp.server",
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

### 🛡️ 硬拦截灾难性命令（v2.2.0 新增）

为防止任何误操作或越权调用直接打到远程 shell，ssh-licco 在所有安全级别下都**无条件**拦截以下灾难性命令模式，**无法通过 `confirm_dangerous=true`、`confirmation_layer=N`、调整 `SSH_SECURITY_LEVEL` 等任何方式绕过**：

- `rm -rf` 作用于绝对路径（含 `/`、`/*`、`/path`、`/path/*`，`-fr` 变体同效）
- `mkfs.*` 任意文件系统格式化
- `dd if=/dev/(zero|random|urandom) of=/dev/(sd|nvme)` 覆写裸盘
- bash fork-bomb（`:(){ :|:& };:` 及空白变体）
- `chmod -R 777 /` / `chmod -R 000 /` 根目录递归改权限
- `> /dev/(sd|nvme)` / `>> /dev/(sd|nvme)` 裸设备重定向

如确需执行上述操作，请直接通过 SSH 登录服务器（绕过 MCP 网关）进行。安全且可逆的替代方案：

```bash
# 旧做法（v2.2.0 之前）：rm -rf /path/to/junk  ← 现已被硬拦截
# 推荐做法：mv 到回收站，约定时间后清理
mv /path/to/junk /tmp/.trash_$(date +%s)/
```

命中硬拦截时会输出 `WARNING` 审计日志（含 category 与命令），便于 SOC 监控。

---

## 🛠️ 可用工具（v2.2.0 维持 9 个；v2.1.0 曾增加的 3 个审批工具因流程闭环风险已下线）

| 工具 | 描述 | 核心能力 |
|------|------|---------|
| `ssh_connect` | 连接管理 | 自动读取环境变量/配置，支持密码+密钥认证，可保存配置，登录后自动执行命令 |
| `ssh_execute` | 命令执行 | 自动连接、智能后台检测、长任务等待、超时控制，支持 nohup/screen/tmux 三种后台模式；v2.2.0 起对灾难性命令（rm -rf 绝对路径、mkfs、raw-disk dd、fork-bomb 等）做**无条件硬拦截** |
| `ssh_disconnect` | 会话管理 | 断开指定会话 OR 列出所有活跃会话 |
| `ssh_file_transfer` | 文件传输 | 上传/下载/列表/写入/追加/删除/创建目录/查看元信息（8 种操作）；v2.1.3+ delete 操作新增 Windows/Unix 敏感路径拦截与路径遍历防护 |
| `ssh_host` | 主机管理 | `action=list/add/remove` 增删查主机配置 |
| `ssh_docker` | Docker 管理 | `action=ps/images/build/logs` 全生命周期管理 |
| `ssh_generate_key` | 密钥生成 | RSA / Ed25519 密钥对 |
| `ssh_session` | screen/tmux 会话 | 持久化远程会话管理（create/send/capture/list/kill），SSH 断开后进程依然存活 |
| `ssh_process` | 进程管理 | 启动/停止/查询远程进程，SSH 端口转发（tunnel_open/tunnel_close/tunnel_list） |

> **关于 v2.1.0 引入的 3 个审批工具**（`ssh_request_approval` / `ssh_approve_command` / `ssh_list_approvals`）：已从 MCP `list_tools()` 移除，**代码已在 v2.2.0 删除**（`ssh_mcp/approval.py`、`ssh_mcp/handlers/approval.py`）。审批流程依赖 AI 自报命令、运维侧背书，存在闭环风险；v2.2.0 的硬拦截更直接——灾难性命令在 MCP 网关层就被拒绝，运维侧不需要再走"先申请再审批"流程。

### 📖 详细文档

- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - 完整 API 参考
- **[docs/skills/ssh-mcp-ops/SKILL.md](docs/skills/ssh-mcp-ops/SKILL.md)** - 运维操作指南

---

## 💡 使用示例

### 示例 1：执行命令

```
用户：帮我查看服务器上的 Docker 容器
AI：调用 ssh_connect → ssh_execute "docker ps"

[执行结果]
CONTAINER ID   IMAGE     COMMAND   STATUS   PORTS
abc123         nginx     "nginx"   Up 2 days 80:80
```

### 示例 2：文件上传

```
用户：把这个文件上传到 /var/www/html
AI：调用 ssh_connect → ssh_file_transfer

[上传成功]
本地：./index.html
远程：/var/www/html/index.html
大小：2.3 KB
```

### 示例 3：Docker 构建（长任务）

```
用户：帮我构建 Docker 镜像
AI：调用 ssh_execute(background=True) 后台执行 docker build...

[后台任务已启动]
Session ID: a1b2c3d4
命令：docker build -t myapp .
使用 ssh_execute(session_id="a1b2c3d4", command="cat /tmp/build.log") 查看进度
```

### 示例 4：数据库检查

```
用户：检查 PostgreSQL 是否正常运行
AI：调用 ssh_execute "pg_isready -h localhost -p 5432"

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
      "command": "python -m ssh_mcp.server",
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
      "command": "python -m ssh_mcp.server",
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
      "command": "python -m ssh_mcp.server",
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
      "command": "python -m ssh_mcp.server",
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
      "command": "python -m ssh_mcp.server",
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

### 🌐 完整环境变量速查（v2.3.0）

> 下表所有变量均被代码读取。**注意**：
> - `SSH_RATE_LIMIT` 是 **bool** 总开关（true/false），`SSH_RATE_LIMIT_MAX` 才是次数上限，两者分开配置
> - 主机密钥检查（strict_host_key_checking）**不通过 env 配置**，请用 `ssh_connect` 工具参数或 `hosts.json`

| 分类 | 变量 | 默认 | 说明 |
|------|------|------|------|
| **安全** | `SSH_SECURITY_LEVEL` | `balanced` | 安全级别：`strict` / `balanced` / `relaxed` |
|  | `SSH_BASE_DIR` | `/home` | 路径校验基目录 |
|  | `SSH_EXTRA_ALLOWED_COMMANDS` | (空) | 额外允许的命令（逗号分隔） |
|  | `SSH_ALLOWED_COMMANDS_FILE` | (空) | 命令白名单 JSON 文件路径 |
|  | `SSH_AUDIT_LOG_PATH` | (空) | 审计日志文件路径 |
| **限流** | `SSH_RATE_LIMIT` | `true` | 限流总开关（bool） |
|  | `SSH_RATE_LIMIT_MAX` | `30` | 限流次数上限 |
|  | `SSH_RATE_LIMIT_WINDOW` | `60` | 限流窗口（秒） |
| **硬拦截** | *(无 env)* | — | 灾难性命令硬拦截，零配置零绕过 |
| **连接默认** | `SSH_HOST` / `SSH_PORT` / `SSH_USER` / `SSH_PASSWORD` | `127.0.0.1` / `22` / `root` / (空) | 单 host 模式默认连接参数 |
|  | `SSH_TIMEOUT` | `60` | 连接超时（秒） |
|  | `SSH_KEEPALIVE_INTERVAL` | `30` | keepalive 间隔（秒） |
|  | `SSH_SESSION_TIMEOUT` | `7200` | 会话超时（秒） |
|  | `SSH_CLIENT_TYPE` | `paramiko` | SSH 客户端实现：`paramiko` / `asyncssh` |
|  | `SSH_FORCE_ENV_CONFIG` | `false` | 强制 env 配置覆盖 hosts.json |
|  | `SSH_SUDO_PASSWORD` | (空) | sudo 密码，配合 `use_sudo=true` 走 `sudo -S` |

---

## ⚠️ 依赖版本兼容性

### 已知依赖冲突

以下依赖版本冲突已在测试环境中验证，**不影响 ssh-licco 的正常使用**：

#### 1. starlette 版本冲突

```
fastapi 需要 starlette<0.51.0
但安装了 starlette 0.52.1
```

**影响范围：**
- ✅ **ssh-licco**: 无影响，正常工作
- ⚠️ **fastapi**: 可能存在兼容性问题（如果同时使用 fastapi）

**解决方案：**
- 如果只使用 ssh-licco，可以忽略此警告
- 如果同时使用 fastapi，建议：
  ```bash
  pip install starlette==0.50.0
  ```

#### 2. cryptography 版本冲突

```
pyopenssl 需要 cryptography<45
但安装了 cryptography 46.0.5
```

**影响范围：**
- ✅ **ssh-licco**: 无影响，正常工作
- ⚠️ **pyopenssl**: 可能存在兼容性问题（如果同时使用 pyopenssl）

**解决方案：**
- 如果只使用 ssh-licco，可以忽略此警告
- 如果同时使用 pyopenssl，建议：
  ```bash
  pip install cryptography==44.0.0
  ```

### 测试环境

**测试通过的配置：**
- ✅ starlette 0.52.1 + ssh-licco 0.4.1
- ✅ cryptography 46.0.5 + ssh-licco 0.4.1
- ✅ mcp 1.26.0 + ssh-licco 0.4.1

**测试场景：**
- ✅ SSH 连接和执行命令
- ✅ 文件上传和下载
- ✅ 后台任务执行
- ✅ Docker 构建和监控
- ✅ 多语言后台命令自动检测

### 为什么允许这些冲突？

ssh-licco 的核心依赖是：
- `mcp` - MCP 协议实现
- `asyncssh` - SSH 客户端
- `paramiko` - SSH 客户端（稳定模式）
- `pydantic` - 数据验证

而 `starlette` 和 `cryptography` 是通过 `mcp` 间接引入的。ssh-licco 本身不直接使用这些库的 API，因此版本冲突不会影响 ssh-licco 的功能。

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

## 🧪 测试

### 测试状态

| 指标 | 状态 |
|------|------|
| **测试用例** | 418 passed, 0 skipped |
| **覆盖率** | 16 个源模块全覆盖 |
| **测试框架** | pytest + pytest-asyncio |

### 测试模块覆盖

| 源模块 | 测试文件 | 用例数 |
|--------|----------|--------|
| `exceptions.py` | `test_exceptions.py` | 7 |
| `connection_config.py` | `test_connection_config.py` | 8 |
| `security.py` | `test_security.py` | 24 |
| `logging_config.py` | `test_logging_config.py` | 8 |
| `audit_logger.py` | `test_audit_logger.py` | 12 |
| `executor.py` | `test_executor.py` | 8 |
| `watchdog.py` | `test_watchdog.py` | 18 |
| `key_manager.py` | `test_key_manager.py` | 6 |
| `config_manager.py` | `test_config_manager.py` | 10 |
| `clients/interface.py` | `test_factory.py` | 10 |
| `clients/paramiko_client.py` | `test_paramiko_client.py` | 18 |
| `clients/factory.py` | `test_factory.py` | 10 |
| `session_manager.py` | `test_session_manager.py` | 18 |
| `connection_pool.py` | `test_connection_pool.py` | 10 |
| `batch_executor.py` | `test_batch_executor.py` | 10 |
| `server.py` | `test_server.py` | 30+ |
| `service.py` | `test_service.py` | 14 |

### 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_security.py -v

# 查看覆盖率
pytest --cov=ssh_mcp --cov-report=term-missing
```

---

## 📊 版本历史