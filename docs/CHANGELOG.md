# 更新日志 (CHANGELOG)

本文档记录 SSH LICCO 项目的所有重要更新。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [0.2.0] - 2026-03-01

### 新增
- **统一异常体系** - 8种异常类型，便于错误处理
  - `SSHException` - 基础异常
  - `ConnectionException` - 连接异常
  - `AuthenticationException` - 认证异常
  - `CommandExecutionException` - 命令执行异常
  - `FileTransferException` - 文件传输异常
  - `SessionException` - 会话异常
  - `TimeoutException` - 超时异常
  - `ConfigurationException` - 配置异常

- **日志管理系统** - 单例模式，支持控制台和文件日志
  - `SSHLogger` - 日志管理器类
  - `get_logger()` - 便捷获取日志实例
  - 支持设置日志级别
  - 支持添加文件日志处理器

- **业务服务层** - 统一的连接和会话管理
  - `SSHService` - 核心服务类
  - 健康检查功能 (`health_check`)
  - 会话管理 (`connect`, `disconnect`, `list_sessions`)
  - 连接信息追踪 (`ConnectionInfo`)

- **可插拔客户端架构** - 多种 SSH 客户端支持
  - `SSHClientInterface` - 抽象接口
  - `SSHClientFactory` - 客户端工厂
  - `ParamikoClient` - 纯 Python 实现
  - `FabricClient` - 高级 API
  - `AsyncSSHClient` - 异步高性能
  - `SSH2Client` - C 扩展

### 改进
- 设置 **AsyncSSH** 为默认客户端
- 分层架构设计，职责分离
- 完整的类型提示
- 性能监控（连接延迟、传输速度）

### 移除
- 移除 System SSH 客户端

---

## [0.1.0] - 2026-03-01

### 新增
- **核心功能**
  - MCP 服务器基础架构
  - SSH 连接管理
  - 会话管理（创建、列出、断开）
  - 命令执行功能
  - SFTP 文件传输（上传、下载、列表）
  - SSH 密钥生成和管理
  - 长连接支持（自动保活）
  - 可配置会话超时

- **工具**
  - `ssh_config` - 配置 SSH 连接信息
  - `ssh_login` - 使用保存的配置登录
  - `ssh_connect` - 直接连接 SSH
  - `ssh_execute` - 执行命令
  - `ssh_disconnect` - 断开连接
  - `ssh_list_sessions` - 列出所有会话
  - `ssh_generate_key` - 生成 SSH 密钥
  - `ssh_file_transfer` - SFTP 文件传输

- **配置方式**
  - 环境变量配置
  - 配置文件 (hosts.json)
  - MCP 注册表配置
  - `ssh_connect` - 直接连接 SSH
  - `ssh_execute` - 执行命令
  - `ssh_disconnect` - 断开连接
  - `ssh_list_sessions` - 列出活跃会话
  - `ssh_generate_key` - 生成 SSH 密钥
  - `ssh_file_transfer` - SFTP 文件传输

- **多客户端支持**
  - Paramiko 客户端（内置）
  - Fabric 客户端支持
  - AsyncSSH 客户端支持
  - SSHClientFactory 工厂模式
  
- **长连接功能**
  - 自动保活机制（默认 30 秒）
  - 可配置会话超时（默认 2 小时）
  - 避免频繁连接导致账户锁定

- **异常处理**
  - 统一的异常基类 SSHException
  - ConnectionException - 连接相关异常
  - AuthenticationException - 认证相关异常
  - CommandExecutionException - 命令执行异常
  - FileTransferException - 文件传输异常
  - SessionException - 会话管理异常

- **日志系统**
  - 多级日志（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 文件日志处理器
  - 控制台日志处理器
  - 可配置的日志格式

- **配置管理**
  - 支持 server.json 配置文件
  - 支持 ~/.ssh/mcp_config.json
  - 支持环境变量配置
  - 支持多个预配置主机

- **服务层 API**
  - SSHService 高级服务层
  - HealthStatus 健康检查
  - 单例模式实现

### 技术栈
- Python 3.10+
- MCP SDK 1.0+
- Paramiko 3.4.0+
- Pydantic 2.0+
- asyncio 异步架构

### 文档
- README.md - 项目介绍和快速开始
- USAGE.md - 详细使用指南
- CONFIG_GUIDE.md - 配置说明
- DOCKER_MCP_TIMEOUT.md - Docker 相关问题说明
- docs/API_REFERENCE.md - API 参考文档
- docs/TROUBLESHOOTING.md - 故障排除指南
- docs/CONTRIBUTING.md - 贡献指南

### 安全性
- 密码本地加密存储
- 支持 SSH 密钥认证
- 支持 Agent 转发
- 文件权限检查

---

## 版本说明

### 版本号说明
- **主版本号 (MAJOR)**: 不兼容的 API 更改
- **次版本号 (MINOR)**: 向后兼容的功能添加
- **修订号 (PATCH)**: 向后兼容的 Bug 修复

### 发布周期
- 主版本：根据重大功能更新
- 次版本：每月发布
- 修订版：根据需要随时发布

---

## 迁移指南

### 从 0.0.x 迁移到 0.1.0

#### API 变更

1. **连接配置**
```python
# 旧版本
config = {
    "host": "192.168.1.100",
    "username": "root"
}

# 新版本
from ssh_mcp import ConnectionConfig
config = ConnectionConfig(
    host="192.168.1.100",
    username="root"
)
```

2. **异常处理**
```python
# 旧版本
try:
    connect()
except Exception as e:
    print(f"Error: {e}")

# 新版本
from ssh_mcp import ConnectionException, AuthenticationException
try:
    service.connect(config)
except ConnectionException as e:
    print(f"Connection failed: {e.message}")
except AuthenticationException as e:
    print(f"Auth failed: {e.message}")
```

3. **日志**
```python
# 旧版本
import logging
logger = logging.getLogger(__name__)

# 新版本
from ssh_mcp import get_logger
logger = get_logger(__name__)
```

---

## 已知问题

### 0.1.0

1. **Windows 平台信号处理**
   - 问题：Windows 不支持 `loop.add_signal_handler()`
   - 影响：优雅关闭可能不完整
   - 临时方案：手动断开连接
   - 状态：计划在下个版本修复

2. **大文件传输**
   - 问题：>1GB 文件可能传输失败
   - 影响：传输中断
   - 临时方案：使用压缩或分块传输
   - 状态：正在优化

---

## 计划中的功能

### 0.2.0 (计划中)
- [ ] 支持 SSH 端口转发
- [ ] 支持 X11 转发
- [ ] 支持 SOCKS 代理
- [ ] 改进的并发性能
- [ ] 连接池支持
- [ ] 自动重连机制

### 0.3.0 (未来)
- [ ] 支持更多的 SSH 客户端后端
- [ ] Web 界面管理
- [ ] 批量操作支持
- [ ] 脚本执行引擎
- [ ] 配置管理界面

---

## 贡献者

感谢所有为这个项目做出贡献的人！

完整贡献者列表：https://github.com/Echoqili/ssh-licco/graphs/contributors

---

## 相关链接

- [GitHub 仓库](https://github.com/Echoqili/ssh-licco)
- [PyPI 页面](https://pypi.org/project/ssh-licco/)
- [问题追踪](https://github.com/Echoqili/ssh-licco/issues)
- [讨论区](https://github.com/Echoqili/ssh-licco/discussions)

---

**注意**: 此更新日志从版本 0.1.0 开始维护。更早的版本未详细记录。
