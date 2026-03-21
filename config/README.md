# SSH 配置文件说明

## 📍 配置文件位置

### 项目根目录配置（优先）
```
d:\pyworkplace\ssh-mcp\config\ssh-hosts.json
```

### 用户主目录配置（后备）
```
C:\Users\Administrator\.ssh\mcp_config.json
```

## 🎯 优先级说明

1. **项目根目录配置** (`config/ssh-hosts.json`) - 优先级最高 ✅
   - 如果存在，优先使用
   - 适合团队共享配置
   - 可以加入版本控制

2. **用户主目录配置** (`~/.ssh/mcp_config.json`) - 后备
   - 如果项目配置不存在，使用此配置
   - 适合个人全局配置
   - 不加入版本控制

## 📝 配置示例

```json
{
  "ssh_hosts": [
    {
      "name": "development",
      "host": "192.168.1.100",
      "port": 22,
      "username": "developer",
      "password": "",
      "timeout": 60,
      "keepalive_interval": 30,
      "session_timeout": 7200
    },
    {
      "name": "production",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "",
      "timeout": 30,
      "keepalive_interval": 60,
      "session_timeout": 3600
    }
  ]
}
```

## 🔧 使用方法

### 方式 1：使用配置的主机名
```python
ssh_connect({
  "name": "production"  // 使用 config/ssh-hosts.json 中的配置
})
```

### 方式 2：直接指定连接参数（优先级更高）
```python
ssh_connect({
  "host": "43.143.207.242",
  "username": "root",
  "password": "your_password"
})
```

## 🚀 快速开始

1. 复制示例配置：
   ```bash
   cp config/ssh-hosts.example.json config/ssh-hosts.json
   ```

2. 编辑 `config/ssh-hosts.json`，填入你的服务器信息

3. 使用配置：
   ```python
   ssh_connect({
     "name": "development"
   })
   ```

## 📋 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 主机名称（用于引用） |
| `host` | string | ✅ | SSH 服务器地址 |
| `port` | integer | ❌ | SSH 端口（默认：22） |
| `username` | string | ❌ | SSH 用户名（默认：root） |
| `password` | string | ❌ | SSH 密码（可选，建议使用密钥） |
| `timeout` | integer | ❌ | 连接超时（秒，默认：60） |
| `keepalive_interval` | integer | ❌ | 心跳间隔（秒，默认：30） |
| `session_timeout` | integer | ❌ | 会话超时（秒，默认：7200） |

## 🔒 安全建议

- ✅ 不要将密码提交到版本控制
- ✅ 使用 SSH 密钥认证代替密码
- ✅ 生产环境配置使用环境变量
- ✅ 定期审查 SSH 配置

## 📖 更多资源

- [连接优先级配置指南](../CONNECTION_PRIORITY_MODES.md)
- [SSH 配置最佳实践](../docs/SSH_BEST_PRACTICES.md)
