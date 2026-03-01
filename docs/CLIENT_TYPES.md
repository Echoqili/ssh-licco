# SSH 客户端类型配置指南

SSH LICCO 支持多种 SSH 客户端实现，你可以根据需求选择不同的客户端。

## 📦 支持的客户端类型

| 客户端 | 类型 | 特点 | 安装 | 适用场景 |
|--------|------|------|------|---------|
| **Paramiko** | 同步 | 纯 Python，功能完善，稳定可靠 | 内置 | 默认推荐，适合大多数场景 |
| **Fabric** | 同步 | 高级 API，易用性强，基于 Paramiko | `pip install fabric` | 需要高级功能，如批量操作 |
| **AsyncSSH** | 异步 | 高并发性能，异步架构 | `pip install asyncssh` | 高并发、大量连接场景 |
| **SSH2** | 同步 | C 扩展，极速性能 | `pip install ssh2-python` | 对性能要求极高的场景 |

## 🔧 配置方式

### 方式 1：在 MCP 配置中全局指定

在 MCP 配置文件中设置 `SSH_CLIENT_TYPE` 环境变量：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_CLIENT_TYPE": "paramiko"
      }
    }
  }
}
```

**支持的值：**
- `"paramiko"` - 使用 Paramiko 客户端（默认）
- `"fabric"` - 使用 Fabric 客户端
- `"asyncssh"` - 使用 AsyncSSH 客户端
- `"ssh2"` - 使用 SSH2 客户端

### 方式 2：在连接时指定

使用 `ssh_connect` 工具时，可以指定 `client_type` 参数：

```json
{
  "name": "ssh_connect",
  "arguments": {
    "host": "192.168.1.100",
    "username": "root",
    "password": "secret",
    "client_type": "fabric"
  }
}
```

### 方式 3：在配置文件中为每个服务器指定

在 `config/hosts.json` 中为每个服务器配置不同的客户端：

```json
{
  "ssh_hosts": [
    {
      "name": "服务器 1",
      "host": "192.168.1.100",
      "username": "root",
      "password": "secret1",
      "client_type": "paramiko"
    },
    {
      "name": "服务器 2",
      "host": "192.168.1.101",
      "username": "admin",
      "password": "secret2",
      "client_type": "fabric"
    },
    {
      "name": "服务器 3",
      "host": "192.168.1.102",
      "username": "user",
      "password": "secret3",
      "client_type": "asyncssh"
    }
  ]
}
```

然后连接时会自动使用配置的客户端类型：

```
连接"服务器 2"
```

## 📊 客户端类型对比

### Paramiko（推荐默认）

**优点：**
- ✅ 纯 Python 实现，跨平台兼容性好
- ✅ 功能完善，支持所有 SSH 功能
- ✅ 稳定可靠，社区活跃
- ✅ 无需额外安装，内置支持

**缺点：**
- ❌ 同步架构，并发性能一般
- ❌ 性能不是最优

**适用场景：**
- 日常使用
- 单个或少量连接
- 需要稳定性的生产环境

### Fabric

**优点：**
- ✅ 高级 API，更易使用
- ✅ 基于 Paramiko，功能丰富
- ✅ 支持批量操作
- ✅ 更好的命令执行体验

**缺点：**
- ❌ 需要额外安装
- ❌ 同步架构

**适用场景：**
- 需要批量操作多个服务器
- 需要更友好的 API
- 复杂的部署任务

### AsyncSSH

**优点：**
- ✅ 异步架构，高并发性能
- ✅ 资源占用低
- ✅ 适合大量连接

**缺点：**
- ❌ 需要额外安装
- ❌ 异步 API 可能需要适配

**适用场景：**
- 高并发场景
- 同时管理大量服务器
- 需要异步集成的应用

### SSH2

**优点：**
- ✅ C 扩展，性能最佳
- ✅ 速度快
- ✅ 资源占用低

**缺点：**
- ❌ 需要编译安装
- ❌ 跨平台兼容性可能有问题
- ❌ 社区相对较小

**适用场景：**
- 对性能要求极高
- 大规模自动化操作
- 性能敏感的应用

## 🎯 选择建议

### 日常使用
```json
{
  "SSH_CLIENT_TYPE": "paramiko"
}
```

### 批量操作
```json
{
  "SSH_CLIENT_TYPE": "fabric"
}
```

### 高并发
```json
{
  "SSH_CLIENT_TYPE": "asyncssh"
}
```

### 性能关键
```json
{
  "SSH_CLIENT_TYPE": "ssh2"
}
```

## 🔍 查看当前使用的客户端

连接后，查看会话信息可以看到使用的客户端类型：

```
查看当前会话
```

输出示例：
```
活跃会话:
- Session ID: xxx-xxx-xxx
  主机：192.168.1.100:22
  用户名：root
  客户端类型：fabric
  连接时间：2024-01-15T10:30:00
```

## 📝 完整示例

### 示例 1：在 Trae 中使用不同客户端

```json
// Trae MCP 配置
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_CLIENT_TYPE": "paramiko"
      }
    }
  }
}
```

使用：
```
连接 192.168.1.100，用户名 root，密码 secret
```

### 示例 2：混合使用不同客户端

配置文件 `config/hosts.json`：
```json
{
  "ssh_hosts": [
    {
      "name": "主服务器",
      "host": "192.168.1.100",
      "username": "root",
      "password": "secret1",
      "client_type": "paramiko"
    },
    {
      "name": "备份服务器",
      "host": "192.168.1.101",
      "username": "admin",
      "password": "secret2",
      "client_type": "fabric"
    }
  ]
}
```

使用：
```
连接"主服务器"  // 使用 paramiko
连接"备份服务器"  // 使用 fabric
```

### 示例 3：临时切换客户端

```
// 默认使用 paramiko
连接 192.168.1.100，用户名 root，密码 secret

// 临时使用 fabric 连接另一个服务器
连接 192.168.1.101，用户名 admin，密码 secret2，client_type=fabric
```

## ⚙️ 客户端特定配置

### Fabric 配置

Fabric 客户端支持额外配置：

```json
{
  "ssh_hosts": [
    {
      "name": "Fabric 服务器",
      "host": "192.168.1.100",
      "client_type": "fabric",
      "config": {
        "connect_timeout": 30,
        "command_timeout": 60,
        "load_system_configs": false
      }
    }
  ]
}
```

### AsyncSSH 配置

AsyncSSH 客户端支持异步特定配置：

```json
{
  "ssh_hosts": [
    {
      "name": "AsyncSSH 服务器",
      "host": "192.168.1.100",
      "client_type": "asyncssh",
      "config": {
        "max_concurrent_sessions": 10,
        "ping_interval": 30
      }
    }
  ]
}
```

## 🐛 故障排除

### 问题 1：客户端不可用

**错误信息：**
```
Client type 'fabric' is not available. Please install it first.
```

**解决方案：**
```bash
pip install fabric
```

### 问题 2：客户端切换失败

**错误信息：**
```
Failed to switch client type from paramiko to asyncssh
```

**解决方案：**
1. 确保新客户端已安装
2. 断开当前连接
3. 重新连接使用新客户端

### 问题 3：性能不如预期

**解决方案：**
1. 尝试不同的客户端类型
2. 检查网络延迟
3. 调整保活间隔和超时设置
4. 启用压缩

## 📚 相关资源

- [配置指南](CONFIG_GUIDE.md)
- [使用指南](USAGE.md)
- [API 参考](docs/API_REFERENCE.md)
- [故障排除](docs/TROUBLESHOOTING.md)

## 💡 最佳实践

1. **默认使用 Paramiko** - 稳定性和兼容性最佳
2. **批量操作用 Fabric** - 更友好的 API
3. **高并发选 AsyncSSH** - 异步架构优势
4. **性能关键用 SSH2** - C 扩展最快速
5. **不要频繁切换** - 保持连接稳定性
6. **测试后再部署** - 在生产环境前充分测试

---

**提示**：选择合适的客户端类型可以显著提升性能和用户体验！
