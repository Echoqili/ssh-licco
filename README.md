# 🚀 SSH LICCO

<!-- mcp-name: io.github.Echoqili/ssh-licco -->

[![PyPI version](https://badge.fury.io/py/ssh-licco.svg)](https://badge.fury.io/py/ssh-licco)
[![Python 3.10-3.13](https://img.shields.io/badge/python-3.10--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-green.svg)](https://registry.modelcontextprotocol.io/)

> **让 AI 帮你操作服务器！** 通过自然语言对话，AI 可以帮你执行命令、管理文件、查看日志、部署应用等。

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

---

## 🔐 安全配置（v0.2.1+）

### 多级安全策略

ssh-licco 提供三种安全级别，可根据使用场景灵活配置：

| 级别 | 名称 | 适用场景 | 安全评分 |
|------|------|----------|----------|
| **STRICT** | 严格模式 | 生产环境、公共服务器 | 最高 ⭐⭐⭐ |
| **BALANCED** | 平衡模式 | 开发环境、个人服务器（默认） | 高 ⭐⭐ |
| **RELAXED** | 宽松模式 | 测试环境、完全信任的服务器 | 中等 ⭐ |

### 快速配置

#### 方式 1：环境变量（推荐）

**Windows PowerShell**:
```powershell
# 设置安全级别
$env:SSH_SECURITY_LEVEL = "balanced"

# 添加额外允许的命令
$env:SSH_EXTRA_ALLOWED_COMMANDS = "git,pip,npm"

# 启动服务器
python -m ssh_mcp.server
```

**Linux/Mac**:
```bash
export SSH_SECURITY_LEVEL="balanced"
export SSH_EXTRA_ALLOWED_COMMANDS="git,pip,npm"
python -m ssh_mcp.server
```

#### 方式 2：MCP 配置文件

编辑 `mcp.config.json`:

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

### 环境变量详解

#### SSH_SECURITY_LEVEL

设置安全级别（默认：`balanced`）

- `strict` - 严格模式，最严格验证
- `balanced` - 平衡模式，适度验证（推荐）
- `relaxed` - 宽松模式，最小验证

#### SSH_EXTRA_ALLOWED_COMMANDS

添加额外允许的命令，逗号分隔：

```bash
# Web 开发者
export SSH_EXTRA_ALLOWED_COMMANDS="git,npm,docker,composer"

# Python 开发者
export SSH_EXTRA_ALLOWED_COMMANDS="pip,poetry,python3"

# 系统管理员
export SSH_EXTRA_ALLOWED_COMMANDS="sudo,apt,yum,systemctl"
```

#### SSH_BASE_DIR

设置允许访问的基础目录（默认：`/home`）

```bash
export SSH_BASE_DIR="/var/www"
```

### 允许的命令

#### 所有级别都允许（基础命令）

```
ls, cat, grep, find, docker, systemctl, ps, top
cp, mv, rm, mkdir, tar, gzip
... 等常用命令
```

#### RELAXED 级别额外允许

```
sudo, git, pip, npm, curl, wget
python3, node, vim, ssh, scp
... 等开发和管理命令
```

### 安全保护

- ✅ **命令注入防护** - 阻止管道、重定向等危险字符
- ✅ **路径遍历防护** - 阻止 `../../../etc/passwd` 等攻击
- ✅ **敏感文件保护** - 禁止访问 `/etc/shadow` 等敏感文件
- ✅ **危险操作检测** - 阻止 `rm -rf /` 等危险命令
- ✅ **友好错误提示** - 提供解决方案和相似命令建议

### 使用示例

#### 生产环境（最高安全）

```bash
export SSH_SECURITY_LEVEL="strict"
python -m ssh_mcp.server
```

#### 开发环境（推荐配置）

```bash
export SSH_SECURITY_LEVEL="balanced"
export SSH_EXTRA_ALLOWED_COMMANDS="git,npm,docker"
export SSH_BASE_DIR="/var/www"
python -m ssh_mcp.server
```

#### 测试环境（完全信任）

```bash
export SSH_SECURITY_LEVEL="relaxed"
export SSH_EXTRA_ALLOWED_COMMANDS="sudo,apt,systemctl"
python -m ssh_mcp.server
```

### 详细文档

完整的安全配置指南请参考：[`SECURITY_CONFIG_GUIDE.md`](SECURITY_CONFIG_GUIDE.md)

---

#### 方式 B：配置文件

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
      "timeout": 30,
      "keepalive_interval": 30,
      "session_timeout": 7200,
      "banner_timeout": 60
    }
  ]
}
```

### 3️⃣ 开始使用

重启 AI 应用后，直接用自然语言对话：

#### 示例 1：查看服务器状态
```
帮我看看服务器的负载情况
```

#### 示例 2：执行命令
```
在服务器上执行 docker ps 查看运行中的容器
```

#### 示例 3：管理文件
```
列出 /var/log 目录下的所有文件
```

#### 示例 4：安装软件
```
在服务器上安装 nginx
```

#### 示例 5：上传文件
```
把本地的 config.yaml 上传到服务器的 /etc 目录
```

---

## 🔥 核心功能

### 1. 长连接支持（避免账户锁定）

频繁连接 SSH 服务器可能导致账户被锁定。SSH LICCO 默认启用长连接和自动保活：

- **自动保活**：每 30 秒发送心跳包
- **持久会话**：默认保持 2 小时
- **可配置**：根据需求调整参数

```json
{
  "SSH_KEEPALIVE_INTERVAL": "30",
  "SSH_SESSION_TIMEOUT": "7200"
}
```

### 2. 连接池（高性能）

- **连接复用**：避免频繁建立连接
- **健康检查**：自动检测并回收无效连接
- **线程安全**：支持并发访问

```python
from ssh_mcp import ConnectionConfig, PoolConfig, ConnectionPool

pool_config = PoolConfig(
    min_size=1,
    max_size=10,
    max_idle_time=300
)

config = ConnectionConfig(host="192.168.1.100", username="admin")
pool = ConnectionPool(config, pool_config)
pool.initialize()

with pool.acquire() as client:
    result = client.execute_command("ls -la")
```

### 3. 批量执行（多主机管理）

- **并行执行**：多主机同时执行命令
- **失败隔离**：单主机异常不影响其他
- **异步支持**：高并发批量操作

```python
from ssh_mcp import ConnectionConfig, BatchExecutor

hosts = [
    ConnectionConfig(host="192.168.1.100", username="admin"),
    ConnectionConfig(host="192.168.1.101", username="admin"),
    ConnectionConfig(host="192.168.1.102", username="admin"),
]

executor = BatchExecutor(hosts, max_workers=10)
result = executor.execute("uptime")

print(f"成功：{result.success_count}, 失败：{result.failed_count}")
```

### 4. 审计日志

- **结构化日志**：JSON 格式便于分析
- **操作记录**：连接、命令、文件传输
- **认证审计**：成功/失败认证记录

```python
from ssh_mcp import get_audit_logger

audit = get_audit_logger("logs/audit.log")
audit.log_command(
    username="admin",
    host="192.168.1.100",
    command="ls -la",
    return_code=0
)
```

### 5. Docker 支持

- **Docker 构建**：支持 Docker 镜像构建
- **状态监控**：查看 Docker 服务状态
- **后台任务**：异步执行长时间任务

### 6. 后台任务管理

- **任务创建**：创建后台任务
- **状态跟踪**：查看任务执行状态
- **结果查询**：获取任务执行结果

---

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
| `ssh_list_hosts` | 列出配置的主机 | 查看已配置的主机列表 |
| `ssh_background_task` | 创建后台任务 | 执行长时间运行的任务 |
| `ssh_task_status` | 查看任务状态 | 获取后台任务的执行状态 |
| `ssh_docker_build` | Docker 镜像构建 | 构建 Docker 镜像 |
| `ssh_docker_status` | Docker 状态检查 | 查看 Docker 服务状态 |
| `ssh_add_host` | 添加主机配置 | 添加新的 SSH 主机配置 |
| `ssh_remove_host` | 移除主机配置 | 删除已配置的 SSH 主机 |

详细使用说明见 [📖 使用指南](USAGE.md)

---

## 🏗️ 架构设计

```
ssh_mcp/
├── clients/              # SSH 客户端层
│   ├── interface.py     # 抽象接口
│   ├── asyncssh_client.py  # AsyncSSH 实现
│   └── factory.py       # 客户端工厂
├── service.py           # 业务服务层
├── session_manager.py   # 会话管理
├── connection_pool.py   # 连接池
├── batch_executor.py    # 批量执行器
├── audit_logger.py      # 审计日志
├── exceptions.py        # 异常体系
└── server.py            # MCP 服务端
```

**设计模式：**
**架构设计：**
- 工厂模式 - SSHClientFactory 动态创建客户端
- 策略模式 - 支持多种 SSH 客户端实现
- 单例模式 - 全局 SSHService 实例
- 上下文管理器 - 自动连接/断开管理

**客户端支持：**
- ✅ **paramiko** - 成熟稳定，Python 社区标准（默认，推荐）⭐
- ✅ **asyncssh** - 异步架构，高并发性能 🚀
- ✅ **fabric** - 简化 API，运维友好 👨‍💻

---

## 🔒 安全注意事项

⚠️ **重要提示：**

1. **密码安全** - 密码仅本地存储，建议使用后清除
2. **不要分享** - 不要在公开场合分享服务器密码
3. **密钥认证** - 优先使用 SSH 密钥认证
4. **普通用户** - 尽量使用普通用户而非 root
5. **文件权限** - 确保配置文件权限为 600
6. **环境变量** - 使用环境变量存储敏感信息

---

## 📚 文档

- [📖 使用指南](USAGE.md) - 详细的工具使用说明
- [⚙️ 配置指南](config/CONFIG_GUIDE.md) - SSH 客户端配置指南
- [📝 API 参考](docs/API_REFERENCE.md) - API 接口文档
- [🤝 贡献指南](docs/CONTRIBUTING.md) - 项目贡献说明

---

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

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

详见 [CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [AsyncSSH](https://github.com/ronf/asyncssh) - 异步 SSH 库

---

## 📬 联系方式

- **项目地址**: https://github.com/Echoqili/ssh-licco
- **问题反馈**: https://github.com/Echoqili/ssh-licco/issues
- **PyPI**: https://pypi.org/project/ssh-licco/
- **MCP Registry**: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

---

<div align="center">

**Made with ❤️ by SSH LICCO Team**

[![Star History Chart](https://api.star-history.com/svg?repos=Echoqili/ssh-licco&type=Date)](https://star-history.com/#Echoqili/ssh-licco&Date)

</div>
