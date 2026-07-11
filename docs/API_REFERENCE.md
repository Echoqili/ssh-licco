# API 参考文档

本文档提供 SSH LICCO 的完整 API 参考。

## 目录

- [核心类](#核心类)
- [SSH 客户端](#ssh-客户端)
- [服务层 API](#服务层-api)
- [安全验证](#安全验证)
- [会话管理](#会话管理)
- [连接池](#连接池)
- [批量执行](#批量执行)
- [看门狗监控](#看门狗监控)
- [审计日志](#审计日志)
- [线程池执行器](#线程池执行器)
- [密钥管理](#密钥管理)
- [配置管理](#配置管理)
- [CLI 命令行](#cli-命令行)
- [异常处理](#异常处理)
- [日志管理](#日志管理)

---

## 核心类

### ConnectionConfig

SSH 连接配置数据类。

```python
from ssh_mcp import ConnectionConfig

config = ConnectionConfig(
    host="192.168.1.100",
    port=22,
    username="root",
    password="secret",
    auth_method="password",  # 或 "private_key", "agent"
    private_key_path="/path/to/key",
    passphrase="key-passphrase",
    timeout=30,
    keepalive_interval=30,
    session_timeout=7200,
    compress=True,
    look_for_keys=True,
    allow_agent=True
)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | str | - | SSH 服务器主机名或 IP |
| port | int | 22 | SSH 端口 |
| username | str | - | SSH 用户名 |
| password | Optional[str] | None | SSH 密码 |
| auth_method | str | "private_key" | 认证方法 |
| private_key_path | Optional[Path] | None | 私钥文件路径 |
| passphrase | Optional[str] | None | 私钥密码 |
| timeout | int | 30 | 连接超时（秒） |
| keepalive_interval | int | 30 | 保活间隔（秒） |
| session_timeout | int | 7200 | 会话超时（秒） |
| compress | bool | True | 启用压缩 |
| look_for_keys | bool | True | 自动查找密钥 |
| allow_agent | bool | True | 允许 SSH Agent |

---

### SessionInfo

会话信息数据类。

```python
from ssh_mcp import SessionInfo, SessionState

info: SessionInfo = session_manager.get_session_info()

print(f"会话 ID: {info.session_id}")
print(f"主机：{info.host}:{info.port}")
print(f"用户名：{info.username}")
print(f"状态：{info.state}")
print(f"连接时间：{info.connected_at}")
print(f"客户端类型：{info.client_type}")
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| session_id | str | 唯一会话标识符 |
| host | str | 连接的主机 |
| port | int | 连接的端口 |
| username | str | 用户名 |
| state | SessionState | 会话状态 |
| connected_at | datetime | 连接时间 |
| last_activity | datetime | 最后活动时间 |
| client_type | ClientType | SSH 客户端类型 |
| command_count | int | 执行的命令数 |
| error_message | Optional[str] | 错误信息 |

---

### SessionState

会话状态枚举。

```python
from ssh_mcp import SessionState

states = [
    SessionState.CONNECTING,    # 连接中
    SessionState.CONNECTED,     # 已连接
    SessionState.AUTHENTICATING, # 认证中
    SessionState.AUTHENTICATED,  # 已认证
    SessionState.EXECUTING,     # 执行中
    SessionState.DISCONNECTED,  # 已断开
    SessionState.ERROR          # 错误
]
```

---

## SSH 客户端

### SSHClientFactory

SSH 客户端工厂类。

```python
from ssh_mcp.clients import SSHClientFactory, ClientType

# 创建默认客户端
client = SSHClientFactory.create(config)

# 创建特定类型的客户端
client = SSHClientFactory.create(config, ClientType.PARAMIKO)

# 设置全局默认客户端
SSHClientFactory.set_default(ClientType.FABRIC)

# 获取可用客户端类型
available = SSHClientFactory.get_available_types()
```

**方法：**

| 方法 | 说明 |
|------|------|
| `create(config, client_type=None)` | 创建 SSH 客户端实例 |
| `set_default(client_type)` | 设置默认客户端类型 |
| `get_default()` | 获取默认客户端类型 |
| `get_available_types()` | 获取所有可用的客户端类型 |
| `is_available(client_type)` | 检查客户端类型是否可用 |

---

### BaseSSHClient

SSH 客户端基类（抽象类）。

```python
from ssh_mcp.clients.interface import BaseSSHClient

class MyCustomClient(BaseSSHClient):
    def connect(self) -> None:
        # 实现连接逻辑
        pass
    
    def execute_command(self, command: str, timeout: int = 30) -> dict:
        # 实现命令执行
        pass
    
    def disconnect(self) -> None:
        # 实现断开连接
        pass
```

**抽象方法：**

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到 SSH 服务器 |
| `execute_command(command, timeout)` | 执行命令 |
| `upload_file(local_path, remote_path)` | 上传文件 |
| `download_file(remote_path, local_path)` | 下载文件 |
| `list_directory(path)` | 列出目录 |
| `disconnect()` | 断开连接 |
| `is_connected()` | 检查连接状态 |

---

### ParamikoClient

基于 Paramiko 的 SSH 客户端实现。

```python
from ssh_mcp.clients.paramiko_client import ParamikoClient

client = ParamikoClient(config)
await client.connect()

result = await client.execute_command("uptime")
print(result["stdout"])

await client.disconnect()
```

---

## 服务层 API

### SSHService

高级 SSH 服务层，提供完整的会话管理。

```python
from ssh_mcp import get_ssh_service, ConnectionConfig

# 获取服务实例（单例）
service = get_ssh_service()

# 创建连接配置
config = ConnectionConfig(
    host="192.168.1.100",
    username="root",
    password="secret"
)

# 连接
info = service.connect(config)
print(f"会话 ID: {info.session_id}")

# 执行命令
result = service.execute_command(info.session_id, "uptime")
print(result["stdout"])

# 健康检查
health = service.health_check(info.session_id)
print(f"状态：{health.status}")
print(f"延迟：{health.latency_ms}ms")

# 列出所有会话
sessions = service.list_sessions()
print(f"活跃会话数：{len(sessions)}")

# 断开连接
service.disconnect(info.session_id)

# 断开所有会话
service.disconnect_all()
```

**方法：**

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `connect(config)` | SessionInfo | 创建新的 SSH 连接 |
| `execute_command(session_id, command, timeout)` | dict | 执行命令 |
| `upload_file(session_id, local, remote)` | dict | 上传文件 |
| `download_file(session_id, remote, local)` | dict | 下载文件 |
| `list_directory(session_id, path)` | dict | 列出目录 |
| `disconnect(session_id)` | None | 断开指定会话 |
| `disconnect_all()` | None | 断开所有会话 |
| `list_sessions()` | list[SessionInfo] | 列出所有会话 |
| `health_check(session_id)` | HealthStatus | 健康检查 |
| `get_session(session_id)` | SSHSession | 获取会话对象 |

---

### HealthStatus

健康检查状态。

```python
from ssh_mcp.service import HealthStatus

health = service.health_check(session_id)

print(f"状态：{health.status.value}")  # HEALTHY, DEGRADED, UNHEALTHY
print(f"延迟：{health.latency_ms}ms")
print(f"最后检查：{health.last_check}")
print(f"错误：{health.error_message}")
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| status | HealthStatus | 健康状态 |
| latency_ms | float | 延迟（毫秒） |
| last_check | datetime | 最后检查时间 |
| error_message | Optional[str] | 错误信息 |

---

## 异常处理

### 异常层次结构

```
SSHException (基类)
├── ConnectionException
│   ├── TimeoutException
│   └── NetworkException
├── AuthenticationException
│   ├── PasswordAuthenticationException
│   └── KeyAuthenticationException
├── CommandExecutionException
├── FileTransferException
└── SessionException
    ├── SessionNotFoundException
    └── SessionTimeoutException
```

---

### SSHException

所有 SSH 异常的基类。

```python
from ssh_mcp import SSHException

try:
    # 某些操作
    pass
except SSHException as e:
    print(f"SSH 错误：{e.message}")
    print(f"原始错误：{e.original_exception}")
```

---

### ConnectionException

连接相关异常。

```python
from ssh_mcp import ConnectionException

try:
    service.connect(config)
except ConnectionException as e:
    print(f"连接失败：{e.message}")
    print(f"主机：{e.host}:{e.port}")
```

**属性：**
- `message`: 错误消息
- `host`: 目标主机
- `port`: 目标端口
- `original_exception`: 原始异常

---

### AuthenticationException

认证失败异常。

```python
from ssh_mcp import AuthenticationException

try:
    service.connect(config)
except AuthenticationException as e:
    print(f"认证失败：{e.message}")
    print(f"用户名：{e.username}")
    print(f"认证方法：{e.auth_method.value}")
```

**属性：**
- `message`: 错误消息
- `username`: 用户名
- `auth_method`: 认证方法

---

### CommandExecutionException

命令执行失败异常。

```python
from ssh_mcp import CommandExecutionException

try:
    result = service.execute_command(session_id, "invalid-command")
except CommandExecutionException as e:
    print(f"命令执行失败：{e.message}")
    print(f"命令：{e.command}")
    print(f"退出码：{e.exit_code}")
    print(f"输出：{e.output}")
```

**属性：**
- `message`: 错误消息
- `command`: 执行的命令
- `exit_code`: 退出码
- `output`: 命令输出
- `stderr`: 标准错误输出

---

### FileTransferException

文件传输失败异常。

```python
from ssh_mcp import FileTransferException

try:
    service.upload_file(session_id, "local.txt", "/remote.txt")
except FileTransferException as e:
    print(f"文件传输失败：{e.message}")
    print(f"本地路径：{e.local_path}")
    print(f"远程路径：{e.remote_path}")
    print(f"方向：{e.direction}")
```

**属性：**
- `message`: 错误消息
- `local_path`: 本地路径
- `remote_path`: 远程路径
- `direction`: 传输方向（upload/download）

---

### SessionException

会话相关异常。

```python
from ssh_mcp import SessionNotFoundException, SessionTimeoutException

try:
    service.execute_command("invalid-session-id", "uptime")
except SessionNotFoundException as e:
    print(f"会话不存在：{e.session_id}")

try:
    service.execute_command(session_id, "uptime")
except SessionTimeoutException as e:
    print(f"会话超时：{e.session_id}")
    print(f"超时时间：{e.timeout_seconds}秒")
```

---

## 日志管理

### get_logger

获取日志记录器。

```python
from ssh_mcp import get_logger

logger = get_logger("my-app")

logger.debug("调试信息")
logger.info("应用启动")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

---

### SSHLogger

日志配置管理类。

```python
from ssh_mcp import SSHLogger

# 设置日志级别
SSHLogger.set_log_level("DEBUG")

# 添加文件处理器
SSHLogger.add_file_handler("logs/ssh-licco.log")

# 添加控制台处理器
SSHLogger.add_console_handler()

# 设置日志格式
SSHLogger.set_log_format("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# 获取日志记录器
logger = SSHLogger.get_logger("my-module")
```

**方法：**

| 方法 | 说明 |
|------|------|
| `set_log_level(level)` | 设置日志级别 |
| `add_file_handler(filename, level)` | 添加文件日志处理器 |
| `add_console_handler(level)` | 添加控制台日志处理器 |
| `set_log_format(format_string)` | 设置日志格式 |
| `get_logger(name)` | 获取日志记录器 |

---

## 使用示例

### 完整示例

```python
from ssh_mcp import (
    get_ssh_service,
    ConnectionConfig,
    SSHException,
    ConnectionException,
    AuthenticationException,
    CommandExecutionException,
    get_logger,
)

# 配置日志
from ssh_mcp import SSHLogger
SSHLogger.set_log_level("INFO")
SSHLogger.add_file_handler("ssh.log")

logger = get_logger("my-ssh-app")

# 获取服务
service = get_ssh_service()

# 创建配置
config = ConnectionConfig(
    host="192.168.1.100",
    port=22,
    username="root",
    password="secret",
    keepalive_interval=30,
    session_timeout=7200
)

try:
    # 连接
    logger.info("正在连接服务器...")
    info = service.connect(config)
    logger.info(f"连接成功：{info.session_id}")
    
    # 执行命令
    logger.info("执行命令：uptime")
    result = service.execute_command(info.session_id, "uptime")
    print(f"输出：{result['stdout']}")
    
    # 健康检查
    health = service.health_check(info.session_id)
    logger.info(f"健康状态：{health.status.value}, 延迟：{health.latency_ms}ms")
    
    # 列出文件
    files = service.list_directory(info.session_id, "/home")
    print(f"文件列表：{files['files']}")
    
    # 断开连接
    service.disconnect(info.session_id)
    logger.info("连接已断开")
    
except ConnectionException as e:
    logger.error(f"连接失败：{e.message}")
except AuthenticationException as e:
    logger.error(f"认证失败：{e.message}")
except CommandExecutionException as e:
    logger.error(f"命令执行失败：{e.message}, 退出码：{e.exit_code}")
except SSHException as e:
    logger.error(f"SSH 错误：{e.message}")
except Exception as e:
    logger.critical(f"未知错误：{e}")
```

---

## 最佳实践

### 1. 使用上下文管理器

```python
from contextlib import contextmanager

@contextmanager
def ssh_session(config):
    service = get_ssh_service()
    info = service.connect(config)
    try:
        yield info
    finally:
        service.disconnect(info.session_id)

# 使用
with ssh_session(config) as info:
    result = service.execute_command(info.session_id, "uptime")
```

### 2. 批量执行命令

```python
commands = ["uptime", "free -h", "df -h"]
results = []

for cmd in commands:
    try:
        result = service.execute_command(session_id, cmd)
        results.append({"command": cmd, "success": True, "output": result["stdout"]})
    except CommandExecutionException as e:
        results.append({"command": cmd, "success": False, "error": e.message})
```

### 3. 健康检查

```python
import time

def monitor_session(service, session_id, interval=60):
    while True:
        try:
            health = service.health_check(session_id)
            if health.status.value == "UNHEALTHY":
                print(f"会话不健康：{health.error_message}")
                break
            print(f"健康：延迟 {health.latency_ms}ms")
        except Exception as e:
            print(f"检查失败：{e}")
        time.sleep(interval)
```

---

## 性能优化

### 1. 连接池

```python
from concurrent.futures import ThreadPoolExecutor

# 使用线程池并发执行
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = []
    for config in configs:
        future = executor.submit(service.connect, config)
        futures.append(future)
    
    for future in futures:
        info = future.result()
        print(f"连接：{info.session_id}")
```

### 2. 命令批处理

```python
# 使用 shell 脚本批量执行
script = """
uptime
free -h
df -h
whoami
"""

result = service.execute_command(session_id, script)
```

---

## 版本兼容性

| SSH LICCO 版本 | Python 版本 | MCP 版本 |
|---------------|-----------|---------|
| 0.5.x | 3.10+ | 1.0+ |
| 0.2.x | 3.10+ | 1.0+ |
| 0.1.x | 3.10+ | 1.0+ |

---

## 安全验证

### SecurityLevel

安全级别枚举。

```python
from ssh_mcp.security import SecurityLevel

levels = [
    SecurityLevel.STRICT,    # 严格模式 - 生产环境
    SecurityLevel.BALANCED,   # 平衡模式 - 开发环境（默认）
    SecurityLevel.RELAXED,    # 宽松模式 - 测试环境
]
```

### CommandValidator

命令安全验证器。

```python
from ssh_mcp.security import CommandValidator, SecurityLevel

# 创建验证器
validator = CommandValidator(SecurityLevel.BALANCED)

# 验证命令
try:
    validator.validate_command("ls -la")
except SecurityError as e:
    print(f"命令不安全: {e}")

# 添加额外允许的命令
validator = CommandValidator(
    SecurityLevel.BALANCED,
    extra_allowed_commands={"git", "pip", "npm"}
)
```

**方法：**

| 方法 | 说明 |
|------|------|
| `validate_command(command)` | 验证命令安全性，不安全时抛出 SecurityError |

### PathValidator

路径安全验证器。

```python
from ssh_mcp.security import PathValidator, SecurityLevel

validator = PathValidator(SecurityLevel.BALANCED, base_dir="/home")

try:
    validator.validate_path("/home/user/file.txt")
except SecurityError as e:
    print(f"路径不安全: {e}")
```

**方法：**

| 方法 | 说明 |
|------|------|
| `validate_path(path)` | 验证路径安全性，不安全时抛出 SecurityError |

### create_validators_from_env

从环境变量创建验证器。

```python
from ssh_mcp.security import create_validators_from_env

cmd_validator, path_validator = create_validators_from_env()
```

---

## 会话管理

### SSHSession

SSH 会话管理类。

```python
from ssh_mcp.session_manager import SSHSession, SessionState
from ssh_mcp import ConnectionConfig

config = ConnectionConfig(host="192.168.1.100", username="root", password="pwd")
session = SSHSession(config)

# 连接
await session.connect()

# 执行命令
result = await session.execute_command("uptime", timeout=30)

# 上传文件
await session.upload_file("/local/file.txt", "/remote/file.txt")

# 下载文件
await session.download_file("/remote/file.txt", "/local/file.txt")

# 列出目录
entries = await session.list_directory("/home")

# 断开连接
await session.disconnect()
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `session_id` | str | 唯一会话标识符 |
| `config` | ConnectionConfig | 连接配置 |
| `state` | SessionState | 会话状态 |
| `is_connected` | bool | 是否已连接 |
| `client` | BaseSSHClient | SSH 客户端实例 |

### SessionManager

会话管理器，管理多个 SSH 会话。

```python
from ssh_mcp.session_manager import SessionManager

manager = SessionManager()

# 创建会话
session = manager.create_session(config)

# 获取会话
session = manager.get_session(session_id)

# 列出所有会话
sessions = manager.list_sessions()

# 关闭会话
manager.close_session(session_id)

# 关闭所有会话
manager.close_all_sessions()
```

**限制：**
- 最大会话数：10
- 每主机最大会话数：3

---

## 连接池

### ConnectionPool

高性能 SSH 连接池。

```python
from ssh_mcp.connection_pool import ConnectionPool, PooledConnection

pool = ConnectionPool(max_size=10, max_idle_time=300)

# 获取连接
conn = await pool.acquire(config)

# 使用连接
result = await conn.client.execute_command("uptime")

# 归还连接
await pool.release(conn)

# 关闭池
await pool.close()
```

**方法：**

| 方法 | 说明 |
|------|------|
| `acquire(config)` | 从池中获取连接 |
| `release(conn)` | 归还连接到池 |
| `close()` | 关闭所有连接 |
| `stats()` | 获取池统计信息 |

### PooledConnection

池化连接包装。

| 属性 | 类型 | 说明 |
|------|------|------|
| `client` | BaseSSHClient | SSH 客户端 |
| `config` | ConnectionConfig | 连接配置 |
| `created_at` | datetime | 创建时间 |
| `last_used` | datetime | 最后使用时间 |

---

## 批量执行

### BatchExecutor

同步批量执行器。

```python
from ssh_mcp.batch_executor import BatchExecutor

configs = [
    ConnectionConfig(host="192.168.1.100", username="root", password="pwd1"),
    ConnectionConfig(host="192.168.1.101", username="root", password="pwd2"),
]

executor = BatchExecutor(max_workers=5)
results = executor.execute_all(configs, "uptime")
```

### AsyncBatchExecutor

异步批量执行器。

```python
from ssh_mcp.batch_executor import AsyncBatchExecutor

executor = AsyncBatchExecutor(max_workers=5)
results = await executor.execute_all(configs, "uptime")
```

---

## 看门狗监控

### Watchdog

任务监控看门狗（单例）。

```python
from ssh_mcp.watchdog import Watchdog, get_watchdog

wd = get_watchdog()

# 注册任务
wd.register_task("deploy-1", "Deploying app", metadata={"env": "prod"})

# 更新心跳
wd.update_heartbeat("deploy-1")

# 更新进度（0-100）
wd.update_progress("deploy-1", 75)

# 捕获异常
wd.capture_exception("deploy-1", ValueError("build failed"))

# 获取事件历史
events = wd.get_events(limit=10)

# 添加恢复回调
wd.add_recovery_callback(lambda task_id: print(f"Recovering {task_id}"))

# 注销任务
wd.unregister_task("deploy-1")

# 启动/停止监控
wd.start()
wd.stop()
```

**数据类：**

| 类名 | 说明 |
|------|------|
| `WatchdogStatus` | 看门狗状态枚举（RUNNING / STOPPED） |
| `WatchdogEvent` | 监控事件（task_id、type、message、details） |
| `TaskInfo` | 任务信息（task_id、description、progress、last_heartbeat） |

### GlobalExceptionHandler

全局异常处理器。

```python
from ssh_mcp.watchdog import GlobalExceptionHandler

handler = GlobalExceptionHandler()
handler.enable()   # 启用全局异常处理
handler.disable()  # 禁用
```

---

## 审计日志

### AuditLogger

JSON 结构化审计日志（单例）。

```python
from ssh_mcp.audit_logger import AuditLogger, get_audit_logger

logger = get_audit_logger()

# 记录操作
logger.log_connect("192.168.1.100", "root")
logger.log_disconnect("192.168.1.100", "root")
logger.log_command("session-1", "ls -la", success=True)
logger.log_command("session-1", "rm -rf /", success=False, error="blocked")
logger.log_file_transfer("session-1", "upload", "/local.txt", "/remote.txt")
logger.log_auth_success("192.168.1.100", "root", "password")
logger.log_auth_failed("192.168.1.100", "root", "password")

# 设置额外字段
logger.set_extra_fields({"service": "api", "version": "1.0"})
```

**方法：**

| 方法 | 说明 |
|------|------|
| `log_connect(host, username)` | 记录连接 |
| `log_disconnect(host, username)` | 记录断开 |
| `log_command(session_id, command, success, error)` | 记录命令 |
| `log_file_transfer(session_id, direction, local, remote)` | 记录文件传输 |
| `log_auth_success(host, username, method)` | 记录认证成功 |
| `log_auth_failed(host, username, method)` | 记录认证失败 |
| `set_extra_fields(fields)` | 设置额外字段 |

---

## 线程池执行器

### ThreadPoolExecutor

线程池执行器（单例），提供 async_exec 装饰器。

```python
from ssh_mcp.executor import ThreadPoolExecutor, get_executor, async_exec

# 获取执行器实例
executor = get_executor()

# 使用 async_exec 装饰器将同步函数转为异步
@async_exec
def blocking_operation():
    import time
    time.sleep(1)
    return "done"

# 调用
result = await blocking_operation()
```

**方法：**

| 方法 | 说明 |
|------|------|
| `submit(fn, *args, **kwargs)` | 提交同步任务到线程池 |
| `shutdown(wait=True)` | 关闭线程池 |

---

## 密钥管理

### KeyManager

SSH 密钥管理器。

```python
from ssh_mcp.key_manager import KeyManager, SSHKeyPair

km = KeyManager()

# 生成 Ed25519 密钥
key_pair = km.generate_ed25519_key(comment="user@host")

# 生成 RSA 密钥
key_pair = km.generate_rsa_key(key_size=4096, comment="user@host")

# 保存密钥
km.save_key(key_pair, "/path/to/key", passphrase="optional")

# 加载密钥（从磁盘文件）
key_pair = km.load_key("/path/to/key", passphrase="optional")

# 从内存 PEM 字符串加载密钥
key_pair = km.load_key_from_str("-----BEGIN OPENSSH PRIVATE KEY-----\n...", passphrase="optional")
```

### SSHKeyPair

密钥对数据类。

| 属性 | 类型 | 说明 |
|------|------|------|
| `key_type` | str | 密钥类型（rsa / ed25519） |
| `private_key` | object | 私钥对象 |
| `public_key_str` | str | 公钥字符串 |
| `fingerprint` | str | 密钥指纹 |
| `comment` | str | 密钥注释 |

---

## 配置管理

### ConfigManager

SSH 配置管理器。

```python
from ssh_mcp.config_manager import ConfigManager, SSHConfig, SSHHost

cm = ConfigManager()

# 加载配置
config = cm.load()

# 保存配置
cm.save(config)

# 列出主机
hosts = cm.list_hosts()

# 添加主机
cm.add_host(SSHHost(name="prod", host="192.168.1.100", username="root"))

# 移除主机
cm.remove_host("prod")

# 获取默认配置
default = ConfigManager.get_default()
```

### SSHConfig / SSHHost / ServerConfig

Pydantic 配置模型。

```python
from ssh_mcp.config_manager import SSHConfig, SSHHost, ServerConfig

# SSH 主机配置
host = SSHHost(
    name="production",
    host="192.168.1.100",
    port=22,
    username="root",
    password="secret",
    timeout=60,
    keepalive_interval=30,
    session_timeout=7200
)

# SSH 配置
config = SSHConfig(hosts=[host], default_host="production")

# 服务器配置
server_config = ServerConfig(
    max_sessions=10,
    max_sessions_per_host=3,
    rate_limit=100
)
```

---

## CLI 命令行

### 子命令

ssh-licco 提供以下 CLI 子命令：

| 子命令 | 说明 | 示例 |
|--------|------|------|
| `exec` | 执行远程命令 | `ssh-licco exec "ls -la"` |
| `upload` | 上传文件 | `ssh-licco upload ./local.txt /remote.txt` |
| `download` | 下载文件 | `ssh-licco download /remote.txt ./local.txt` |
| `docker-build` | 远程 Docker 构建 | `ssh-licco docker-build myapp:latest` |
| `list-hosts` | 列出已配置主机 | `ssh-licco list-hosts` |
| `serve` | 启动 MCP 服务器 | `ssh-licco serve` |

### 连接参数

所有子命令共享以下连接参数：

| 参数 | 环境变量 | 说明 |
|------|----------|------|
| `--host` | `SSH_HOST` | SSH 主机地址 |
| `--port`, `-p` | `SSH_PORT` | SSH 端口（默认 22） |
| `--username`, `-u` | `SSH_USER` | SSH 用户名 |
| `--password` | `SSH_PASSWORD` | SSH 密码 |
| `--connect-timeout` | `SSH_TIMEOUT` | 连接超时（默认 60） |

### exec 参数

| 参数 | 说明 |
|------|------|
| `cmd` | 要执行的命令（必填） |
| `--timeout`, `-t` | 命令超时秒数（默认 60） |

### docker-build 参数

| 参数 | 说明 |
|------|------|
| `image` | Docker 镜像名称和标签（必填） |
| `--context`, `-c` | 构建上下文目录（默认 `.`） |
| `--dockerfile`, `-f` | Dockerfile 路径（默认 `./Dockerfile`） |
| `--timeout`, `-t` | 构建超时秒数（默认 300） |

---

## 相关资源

- [GitHub 仓库](https://github.com/Echoqili/ssh-licco)
- [PyPI 页面](https://pypi.org/project/ssh-licco/)
- [README](../README.md)
