# SSH LICCO 使用指南

## 简介

SSH LICCO 是一个基于 Model Context Protocol (MCP) 的服务器，让 AI 助手能够连接到远程 SSH 服务器执行命令。

### 核心功能

- ✅ SSH 密码认证登录
- ✅ 远程命令执行
- ✅ 多会话管理（最大 10 个并发，每主机 3 个）
- ✅ SSH 密钥生成（RSA / Ed25519）
- ✅ SFTP 文件传输（上传、下载、列表）
- 🔥 **长连接支持** - 自动保活，避免频繁连接导致账户锁定
- 🔥 **可配置会话超时** - 默认 2 小时，最长可配置
- 🔥 **多客户端支持** - 可选择 paramiko（默认）、asyncssh、fabric
- 🔥 **CLI 命令行** - exec / upload / download / docker-build / list-hosts 子命令
- 🔥 **连接池** - 高性能连接复用（PooledConnection + ConnectionPool）
- 🔥 **批量执行** - 多主机并行命令执行（BatchExecutor + AsyncBatchExecutor）
- 🔥 **看门狗监控** - 任务监控、心跳检测、全局异常处理
- 🔥 **审计日志** - JSON 结构化审计记录
- 🔥 **安全验证** - 三级安全策略（STRICT / BALANCED / RELAXED）

---

## 🏗️ 自动安装体系

ssh-licco 采用 **三层架构** 实现零配置启动：

```
用户 → npx ssh-licco
           ↓
    ┌──── ssh-licco.js (Node 层) ────┐
    │  ① 查找 Python 3.10+          │
    │  ② 检测 Anaconda 环境         │
    │  ③ 创建/复用 ~/.ssh-licco-venv │
    │  ④ pip install 安装           │
    │  ⑤ 验证依赖完整性             │
    └──────────┬────────────────────┘
               ↓
    ┌── cli.py (Python 入口) ──────┐
    │  只负责启动 MCP 服务器        │
    └──────────┬────────────────────┘
               ↓
    ┌── SSHMCPServer (MCP 服务) ──┐
    │  提供 SSH 连接、命令执行等    │
    └────────────────────────────┘
```

### 智能安装特性

| 特性 | 说明 |
|------|------|
| **依赖完整性检查** | 每次启动验证所有依赖可导入，缺失则自动修复 |
| **增量更新** | 已有 venv 时不删除，直接 `pip install -e .` 增量安装 |
| **Anaconda 检测** | 自动检测 conda 环境，使用独立 venv 避免冲突 |
| **自动修复** | 依赖损坏时自动重新安装，无需手动干预 |

### 文件说明

| 文件 | 作用 |
|------|------|
| [ssh-licco.js](ssh-licco.js) | Node.js 包装器，环境准备 + 完整性校验 + 启动 |
| [install.js](install.js) | npm postinstall 安装脚本，增量更新 |
| [smart_install.py](smart_install.py) | 独立诊断安装脚本，含 SSH 连接测试 |
| [cli.py](ssh_mcp/cli.py) | Python 入口，只负责启动服务器 |

---

## 安装

### 方式一：npx 一键启动（推荐，零配置）

```bash
npx ssh-licco
```

首次运行自动完成：检测 Python → 创建虚拟环境 → 安装依赖 → 启动 MCP 服务器。**无需手动安装。**

### 方式二：pip 安装（推荐 Python 项目）

```bash
pip install ssh-licco
```

### 方式三：从源码安装

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

配置完成后，重启 Trae 使 MCP 服务器生效。首次启动会自动完成安装。

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

**示例：**
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "root",
  "password": "your_password",
  "timeout": 30
}
```

---

### 2. ssh_login - 登录并执行命令

使用保存的配置登录 SSH 服务器。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | 否 | 登录后执行的命令 |

**示例：**
```json
{
  "command": "uptime && free -h"
}
```

---

### 3. ssh_connect - 直接连接

不依赖配置文件，直接连接 SSH。支持从 `server.json` 读取预配置的主机。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | server.json 中的主机名称 |
| host | string | 否 | SSH 服务器 IP（与 name 二选一） |
| port | number | 否 | SSH 端口，默认 22 |
| username | string | 是 | SSH 用户名 |
| password | string | 否 | SSH 密码 |
| private_key_path | string | 否 | 私钥路径 |
| passphrase | string | 否 | 私钥密码 |
| timeout | number | 否 | 连接超时（秒），默认 30 |
| keepalive_interval | number | 否 | 保活间隔（秒），默认 30 |
| session_timeout | number | 否 | 会话超时（秒），默认 7200（2 小时） |

**示例 1（使用预配置）：**
```json
{
  "name": "我的服务器"
}
```

**示例 2（直接连接）：**
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "root",
  "password": "your_password",
  "keepalive_interval": 30,
  "session_timeout": 7200
}
```

> 💡 **提示**：`keepalive_interval` 和 `session_timeout` 用于长连接功能，避免频繁连接导致账户锁定。
> 
> **SSH_CLIENT_TYPE**: 设置 SSH 客户端类型（可选）
> - `common` - paramiko（默认，稳定可靠）⭐
> - `performance` - asyncssh（高性能）🚀
> - `development` - fabric（简化 API）👨‍💻
> 
> 详见 [CONFIG_GUIDE.md](config/CONFIG_GUIDE.md)

---

### 4. ssh_execute - 执行命令

在已连接的 SSH 会话中执行命令。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | SSH 会话 ID |
| command | string | 是 | 要执行的命令 |

**示例：**
```json
{
  "session_id": "your-session-id",
  "command": "df -h"
}
```

---

### 5. ssh_disconnect - 断开连接

关闭 SSH 会话。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | SSH 会话 ID |

---

### 6. ssh_list_sessions - 列出会话

列出所有活跃的 SSH 会话。

**无需参数**

---

### 7. ssh_generate_key - 生成密钥

生成 SSH 密钥对。

**参数：**

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| key_type | string | ed25519 | 否 | 密钥类型（rsa 或 ed25519） |
| key_size | number | 4096 | 否 | 密钥大小（仅 RSA） |
| save_path | string | ~/.ssh | 否 | 保存路径 |
| comment | string | - | 否 | 密钥注释 |

---

### 8. ssh_file_transfer - SFTP 文件传输

上传、下载文件或列出目录。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | SSH 会话 ID |
| direction | string | 是 | 传输方向（upload/download/list） |
| local_path | string | 否 | 本地文件路径 |
| remote_path | string | 是 | 远程文件路径 |

**示例 1（上传）：**
```json
{
  "session_id": "your-session-id",
  "direction": "upload",
  "local_path": "/local/file.txt",
  "remote_path": "/remote/file.txt"
}
```

**示例 2（下载）：**
```json
{
  "session_id": "your-session-id",
  "direction": "download",
  "local_path": "./file.txt",
  "remote_path": "/remote/file.txt"
}
```

**示例 3（列表）：**
```json
{
  "session_id": "your-session-id",
  "direction": "list",
  "remote_path": "/home"
}
```

---

## 使用示例

### 示例 1：查看服务器状态

**你说：**
```
查看服务器状态
```

**AI 自动执行：**
1. ssh_config - 配置服务器
2. ssh_login - 登录并执行 "uptime && free -h && df -h"

---

### 示例 2：管理文件

**你说：**
```
列出 /var/log 目录的内容
```

**AI 执行：**
```
ssh_connect -> ssh_file_transfer (direction: list, remote_path: /var/log)
```

---

### 示例 3：安装软件

**你说：**
```
在服务器上安装 nginx
```

**AI 执行：**
```
ssh_connect -> ssh_execute (command: "apt update && apt install -y nginx")
```

---

### 示例 4：上传文件

**你说：**
```
把本地的 config.yaml 上传到服务器的 /etc 目录
```

**AI 执行：**
```
ssh_connect -> ssh_file_transfer (direction: upload, local_path: ./config.yaml, remote_path: /etc/config.yaml)
```

---

## 配置文件

### server.json（推荐）

在项目根目录创建 `server.json`，配置多个服务器：

```json
{
  "ssh_hosts": [
    {
      "name": "生产服务器",
      "host": "192.168.1.100",
      "port": 22,
      "username": "root",
      "password": "password123"
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

### ~/.ssh/mcp_config.json

SSH 配置保存在此文件中，供 `ssh_login` 工具使用。

---

## 安全注意事项

⚠️ **重要提示：**

1. **密码安全** - 密码本地存储，建议使用后清除配置文件
2. **不要分享** - 不要在公开场合分享服务器密码
3. **密钥认证** - 优先使用 SSH 密钥认证而非密码
4. **普通用户** - 尽量使用普通用户而非 root 用户
5. **文件权限** - 确保 `server.json` 文件权限设置为 600

---

## 故障排除

### 连接失败

**现象：** 无法连接到 SSH 服务器

**解决方法：**
1. 检查服务器 IP 和端口是否正确
2. 确认用户名和密码正确
3. 检查服务器防火墙是否开放 SSH 端口
4. 尝试使用 `ping` 命令测试服务器是否可达

### 认证失败

**现象：** 用户名或密码错误

**解决方法：**
1. 确认密码正确（注意区分大小写和特殊字符）
2. 尝试使用密钥认证方式
3. 检查服务器的密码策略
4. 确认用户账户是否被锁定

### 配置文件问题

**现象：** 配置文件不生效

**解决方法：**
1. 确认 `server.json` 文件格式正确
2. 检查 JSON 格式是否有语法错误
3. 确保配置文件路径正确
4. 重启 AI 应用使配置生效

### 命令执行失败

**现象：** 执行命令后无响应或报错

**解决方法：**
1. 确认 SSH 连接已建立
2. 检查命令语法是否正确
3. 确认用户权限是否足够
4. 检查服务器资源使用情况

---

## 技术支持

- **问题反馈**: https://github.com/Echoqili/ssh-licco/issues
- **GitHub**: https://github.com/Echoqili/ssh-licco
- **License**: MIT

---

## 🆕 新功能：多客户端支持

### 切换客户端类型

```python
from ssh_mcp.clients import SSHClientFactory, ClientType

# 方式1：全局设置默认客户端
SSHClientFactory.set_default(ClientType.FABRIC)

# 方式2：创建时指定
client = SSHClientFactory.create(config, ClientType.ASYNCSSH)
```

### 获取可用客户端

```python
from ssh_mcp.clients import SSHClientFactory

# 获取所有可用的客户端类型
available = SSHClientFactory.get_available_types()
print(available)  # [ClientType.PARAMIKO, ClientType.FABRIC, ...]
```

---

## 🆕 新功能：服务层 API

### 使用 SSHService

```python
from ssh_mcp import ConnectionConfig, get_ssh_service

# 获取服务实例
service = get_ssh_service()

# 创建配置
config = ConnectionConfig(
    host="192.168.1.100",
    username="root",
    password="password"
)

# 连接
info = service.connect(config)
print(f"会话ID: {info.session_id}")
print(f"客户端类型: {info.client_type.value}")

# 执行命令
result = service.execute_command(info.session_id, "uptime")
print(result["stdout"])

# 健康检查
health = service.health_check(info.session_id)
print(f"状态: {health.status.value}")
print(f"延迟: {health.latency_ms}ms")

# 列出所有会话
sessions = service.list_sessions()
print(f"活跃会话数: {len(sessions)}")

# 断开
service.disconnect(info.session_id)
```

---

## 🆕 新功能：异常处理

### 捕获特定异常

```python
from ssh_mcp import (
    get_ssh_service,
    ConnectionConfig,
    SSHException,
    AuthenticationException,
    ConnectionException,
    CommandExecutionException,
    FileTransferException,
)

service = get_ssh_service()
config = ConnectionConfig(host="192.168.1.100", username="root", password="wrong")

try:
    info = service.connect(config)
except AuthenticationException as e:
    print(f"认证失败: {e.message}")
except ConnectionException as e:
    print(f"连接失败: {e.message}")
except CommandExecutionException as e:
    print(f"命令执行失败: {e.message}, 命令: {e.command}")
except FileTransferException as e:
    print(f"文件传输失败: {e.message}")
except SSHException as e:
    print(f"SSH错误: {e.message}")
```

---

## 🆕 新功能：日志记录

### 基本日志

```python
from ssh_mcp import get_logger

logger = get_logger("my-app")
logger.info("应用启动")
logger.debug("调试信息")
logger.warning("警告")
logger.error("错误")
logger.critical("严重错误")
```

### 配置日志

```python
from ssh_mcp import SSHLogger

# 设置日志级别
SSHLogger.set_log_level("DEBUG")

# 添加文件日志
SSHLogger.add_file_handler("logs/app.log")
```

---

## 🖥️ CLI 命令行工具

ssh-licco 提供完整的命令行接口，支持直接在终端执行 SSH 操作。

### 全局选项

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号 |
| `--host` | SSH 主机地址（或设置 `SSH_HOST` 环境变量） |
| `--port`, `-p` | SSH 端口（默认 22） |
| `--username`, `-u` | SSH 用户名（或设置 `SSH_USER` 环境变量） |
| `--password` | SSH 密码（或设置 `SSH_PASSWORD` 环境变量） |
| `--connect-timeout` | 连接超时秒数（默认 60） |

### exec - 执行远程命令

```bash
# 基本用法
ssh-licco exec --host 192.168.1.100 -u root --password pwd "ls -la /home"

# 使用环境变量配置连接
export SSH_HOST=192.168.1.100
export SSH_USER=root
export SSH_PASSWORD=pwd
ssh-licco exec "uptime"

# 指定超时
ssh-licco exec --timeout 120 "docker ps"
```

**参数：**

| 参数 | 说明 |
|------|------|
| `cmd` | 要执行的命令（必填） |
| `--timeout`, `-t` | 命令超时秒数（默认 60） |

### upload - 上传文件

```bash
ssh-licco upload --host 192.168.1.100 -u root --password pwd ./local.txt /remote/path.txt
```

**参数：**

| 参数 | 说明 |
|------|------|
| `local` | 本地文件路径（必填） |
| `remote` | 远程文件路径（必填） |

### download - 下载文件

```bash
ssh-licco download --host 192.168.1.100 -u root --password pwd /remote/log.txt ./local.log
```

**参数：**

| 参数 | 说明 |
|------|------|
| `remote` | 远程文件路径（必填） |
| `local` | 本地文件路径（必填） |

### docker-build - 远程 Docker 构建

```bash
ssh-licco docker-build --host 192.168.1.100 -u root --password pwd myapp:latest \
  --context /app --dockerfile ./Dockerfile --timeout 600
```

**参数：**

| 参数 | 说明 |
|------|------|
| `image` | Docker 镜像名称和标签，如 `myapp:latest`（必填） |
| `--context`, `-c` | 构建上下文目录（默认 `.`） |
| `--dockerfile`, `-f` | Dockerfile 路径（默认 `./Dockerfile`） |
| `--timeout`, `-t` | 构建超时秒数（默认 300） |

### list-hosts - 列出已配置主机

```bash
ssh-licco list-hosts
ssh-licco list-hosts --json
```

### serve - 启动 MCP 服务器

```bash
ssh-licco serve
# 或直接
ssh-licco
```

---

## 🆕 新功能：连接池

### 使用 ConnectionPool

```python
from ssh_mcp.connection_pool import ConnectionPool, PooledConnection
from ssh_mcp import ConnectionConfig

pool = ConnectionPool(max_size=10, max_idle_time=300)

config = ConnectionConfig(host="192.168.1.100", username="root", password="pwd")

# 获取连接
conn = await pool.acquire(config)

# 使用连接
result = await conn.client.execute_command("uptime")

# 归还连接
await pool.release(conn)

# 关闭池
await pool.close()
```

---

## 🆕 新功能：批量执行

### BatchExecutor（同步）

```python
from ssh_mcp.batch_executor import BatchExecutor
from ssh_mcp import ConnectionConfig

configs = [
    ConnectionConfig(host="192.168.1.100", username="root", password="pwd1"),
    ConnectionConfig(host="192.168.1.101", username="root", password="pwd2"),
]

executor = BatchExecutor(max_workers=5)
results = executor.execute_all(configs, "uptime")

for r in results:
    print(f"{r.host}: {r.stdout}")
```

### AsyncBatchExecutor（异步）

```python
from ssh_mcp.batch_executor import AsyncBatchExecutor

executor = AsyncBatchExecutor(max_workers=5)
results = await executor.execute_all(configs, "uptime")
```

---

## 🆕 新功能：看门狗监控

### Watchdog

```python
from ssh_mcp.watchdog import Watchdog, get_watchdog

wd = get_watchdog()

# 注册任务
wd.register_task("deploy-1", "Deploying app")

# 更新心跳
wd.update_heartbeat("deploy-1")

# 更新进度
wd.update_progress("deploy-1", 75)

# 捕获异常
wd.capture_exception("deploy-1", ValueError("build failed"))

# 注销任务
wd.unregister_task("deploy-1")
```

### GlobalExceptionHandler

```python
from ssh_mcp.watchdog import GlobalExceptionHandler

handler = GlobalExceptionHandler()
handler.enable()   # 启用全局异常处理
handler.disable()  # 禁用
```

---

## 🆕 新功能：审计日志

### AuditLogger

```python
from ssh_mcp.audit_logger import AuditLogger, get_audit_logger

logger = get_audit_logger()

# 记录操作
logger.log_connect("192.168.1.100", "root")
logger.log_command("session-1", "ls -la", success=True)
logger.log_file_transfer("session-1", "upload", "/local.txt", "/remote.txt")
logger.log_disconnect("192.168.1.100", "root")
```

---

## 🧪 测试

### 运行测试

```bash
# 运行全部测试（402 passed, 3 skipped）
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_security.py -v

# 查看覆盖率
pytest --cov=ssh_mcp --cov-report=term-missing
```

### 测试覆盖

所有 17 个源模块均有完整的单元测试覆盖，包括：
- `exceptions` - 异常层次结构
- `connection_config` - Pydantic 连接配置模型
- `security` - 安全验证（CommandValidator / PathValidator）
- `logging_config` - 日志管理
- `audit_logger` - 审计日志
- `executor` - 线程池执行器
- `watchdog` - 看门狗监控
- `key_manager` - SSH 密钥管理
- `config_manager` - 配置管理
- `clients` - SSH 客户端（接口 / Paramiko / 工厂）
- `session_manager` - 会话管理
- `connection_pool` - 连接池
- `batch_executor` - 批量执行
- `cli` - 命令行接口
- `server` - MCP 服务器
- `service` - SSH 服务层
