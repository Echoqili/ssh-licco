# 🔧 SSH 连接优先级配置指南

## 📊 两种模式对比

| 特性 | 灵活模式 (默认) | 强制模式 |
|------|----------------|----------|
| **优先级** | 用户参数 > 配置文件 > 环境变量 | 环境变量 > 用户参数 > 配置文件 |
| **适用场景** | 开发、个人使用 | 生产、企业环境 |
| **灵活性** | 高 ✅ | 低 |
| **安全性** | 中 | 高 ✅ |
| **配置方式** | 默认 | 设置 `SSH_FORCE_ENV_CONFIG=true` |

---

## ✅ 模式 1：灵活模式（默认）

### 优先级顺序
```
1. 用户传入的参数 (最高)
2. 配置文件 (hosts.json)
3. 环境变量 (最低 - 仅作为后备)
```

### MCP 配置示例

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "your_password",
        "SSH_TIMEOUT": "60"
      }
    }
  }
}
```

### 使用场景

#### 场景 A：使用默认配置（不传参数）
```python
# 自动使用环境变量中的配置
ssh_connect()
# ✅ 连接到 192.168.58.130
```

#### 场景 B：临时连接其他服务器
```python
# 用户参数覆盖环境变量
ssh_connect({
  "host": "43.143.207.242",
  "username": "root",
  "password": "other_password"
})
# ✅ 连接到 43.143.207.242 (用户参数生效)
```

### 优点
- ✅ 灵活，可以临时连接不同服务器
- ✅ 环境变量作为默认值，很方便
- ✅ 适合开发、调试环境

### 缺点
- ❌ 无法强制安全策略
- ❌ 用户可能意外连接到未授权的服务器

---

## 🔒 模式 2：强制模式

### 优先级顺序
```
1. 环境变量 (最高 - 强制)
2. 用户传入的参数
3. 配置文件
```

### MCP 配置示例

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "your_password",
        "SSH_TIMEOUT": "60",
        "SSH_FORCE_ENV_CONFIG": "true"  // ← 关键配置
      }
    }
  }
}
```

### 使用场景

#### 场景 A：用户尝试连接其他服务器
```python
# 用户参数被环境变量覆盖
ssh_connect({
  "host": "43.143.207.242",  // ❌ 被忽略
  "username": "root"
})
# 🔒 仍然连接到 192.168.58.130 (环境变量强制生效)
```

#### 场景 B：不传参数
```python
ssh_connect()
# 🔒 连接到 192.168.58.130 (环境变量)
```

### 优点
- ✅ 强制执行安全策略
- ✅ 确保只能连接到授权的服务器
- ✅ 适合生产环境、企业环境

### 缺点
- ❌ 不够灵活
- ❌ 无法临时连接其他服务器

---

## 🎯 如何选择模式

### 选择灵活模式（默认）如果：
- ✅ 你是个人开发者
- ✅ 你需要连接多个不同的服务器
- ✅ 你在开发、测试环境
- ✅ 你信任使用工具的用户

### 选择强制模式如果：
- ✅ 你是企业管理员
- ✅ 你需要强制执行安全策略
- ✅ 你在生产环境
- ✅ 你需要防止用户连接到未授权的服务器

---

## 📝 完整配置示例

### 开发环境配置（灵活模式）

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "developer",
        "SSH_PASSWORD": "dev_password",
        "SSH_TIMEOUT": "60",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200",
        "SSH_CLIENT_TYPE": "paramiko"
      }
    }
  }
}
```

### 生产环境配置（强制模式）

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "prod-server.company.com",
        "SSH_USER": "deploy",
        "SSH_PASSWORD": "secure_password",
        "SSH_TIMEOUT": "30",
        "SSH_KEEPALIVE_INTERVAL": "60",
        "SSH_SESSION_TIMEOUT": "3600",
        "SSH_CLIENT_TYPE": "paramiko",
        "SSH_FORCE_ENV_CONFIG": "true"  // ← 强制模式
      }
    }
  }
}
```

---

## 🔍 调试和验证

### 查看日志

连接时会显示当前使用的模式：

**灵活模式日志：**
```
✅ Using user-provided host: 43.143.207.242
🎯 Final connection target: 43.143.207.242:22
```

**强制模式日志：**
```
🔒 Using FORCE ENV CONFIG mode
🔒 Forced environment host: 192.168.58.130
🎯 Final connection target: 192.168.58.130:22
🔒 FORCE MODE: Environment config overrides user parameters
```

### 测试命令

```python
# 测试当前配置
ssh_connect({
  "host": "test.example.com"
})

# 查看日志，确认使用的配置
```

---

## ⚠️ 注意事项

### 灵活模式
- ⚠️ 用户可能意外连接到错误的服务器
- ⚠️ 无法防止恶意连接
- ✅ 建议在信任的环境中使用

### 强制模式
- ⚠️ 用户无法临时连接其他服务器
- ⚠️ 可能影响开发效率
- ✅ 建议在生产环境中使用
- ✅ 配合审计日志使用

---

## 🔄 切换模式

### 从灵活模式切换到强制模式

1. 修改 MCP 配置
2. 添加 `SSH_FORCE_ENV_CONFIG: "true"`
3. 重启 MCP 服务器

### 从强制模式切换到灵活模式

1. 修改 MCP 配置
2. 删除或设置 `SSH_FORCE_ENV_CONFIG: "false"`
3. 重启 MCP 服务器

---

## 📖 更多资源

- [SSH 配置指南](SSH_CONFIG_GUIDE.md)
- [安全最佳实践](SECURITY_BEST_PRACTICES.md)
- [故障排除](TROUBLESHOOTING.md)
