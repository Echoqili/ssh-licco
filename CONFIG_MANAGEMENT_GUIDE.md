# SSH MCP 配置管理指南

## ✅ 配置优先级

SSH MCP 现在支持多层配置，优先级如下：

### 1️⃣ MCP 配置文件（最高优先级）
**位置**: Trae IDE 中的 MCP 配置
**文件**: `mcp.json`

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "licco123",
        "SSH_PORT": "22",
        "SSH_TIMEOUT": "120"
      }
    }
  }
}
```

✅ **特点**: 
- 优先级最高
- 适合配置主要使用的服务器
- 配置后所有 SSH 命令默认使用此服务器

### 2️⃣ 本地配置文件（中等优先级）
**位置**: `config/hosts.json`

```json
{
  "ssh_hosts": [
    {
      "name": "production",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "",
      "timeout": 120
    },
    {
      "name": "dev-server",
      "host": "192.168.1.100",
      "port": 22,
      "username": "ubuntu",
      "password": "",
      "timeout": 60
    }
  ]
}
```

✅ **特点**:
- 可配置多个服务器
- 通过 `name` 区分
- 支持动态添加/删除

### 3️⃣ 用户参数（最低优先级）
**方式**: 调用工具时直接传递参数

```json
{
  "host": "10.0.0.1",
  "port": 22,
  "username": "admin",
  "password": "xxx"
}
```

✅ **特点**:
- 临时使用
- 灵活性最高
- 优先级最低

---

## 🛠️ 服务器管理工具

### 查看服务器列表

**工具**: `ssh_list_hosts`

**响应示例**:
```
📋 SSH 服务器配置列表

🔹 [优先级 1] MCP 配置文件 (mcp.json)
  主机：192.168.58.130:22
  用户：licco
  密码：***
  超时：120s

🔹 [优先级 2] 本地配置文件 (config/hosts.json)

  1. production
     主机：43.143.207.242:22
     用户：root
     密码：未设置
     超时：120s

  2. dev-server
     主机：192.168.1.100:22
     用户：ubuntu
     密码：未设置
     超时：60s
```

---

### 添加服务器

**工具**: `ssh_add_host`

**参数**:
```json
{
  "name": "test-server",
  "host": "10.0.0.50",
  "port": 22,
  "username": "test",
  "password": "test123",
  "timeout": 60
}
```

**响应**:
```
✅ SSH 服务器已添加!

名称：test-server
主机：10.0.0.50:22
用户：test
超时：60s

💡 使用 '连接 SSH' 命令时指定 name='test-server' 来连接此服务器
```

---

### 删除服务器

**工具**: `ssh_remove_host`

**参数**:
```json
{
  "name": "test-server"
}
```

**响应**:
```
✅ SSH 服务器 'test-server' 已删除
```

---

### 连接服务器

**工具**: `ssh_connect`

**方式 1: 使用 MCP 配置（优先级 1）**
```json
{}  // 不传参数，自动使用 MCP 配置
```

**方式 2: 使用本地配置（优先级 2）**
```json
{
  "name": "production"
}
```

**方式 3: 使用参数（优先级 3）**
```json
{
  "host": "10.0.0.1",
  "username": "admin",
  "password": "xxx"
}
```

---

## 📝 使用场景

### 场景 1: 主要使用一台服务器

**配置**: 在 MCP 配置文件中设置

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "licco123"
      }
    }
  }
}
```

**使用**: 直接使用，无需额外参数
```
连接 SSH  // 自动连接到 192.168.58.130
```

---

### 场景 2: 管理多台服务器

**配置**: 在 `config/hosts.json` 中配置多台服务器

```json
{
  "ssh_hosts": [
    {"name": "prod", "host": "43.143.207.242", "username": "root"},
    {"name": "dev", "host": "192.168.1.100", "username": "ubuntu"},
    {"name": "test", "host": "10.0.0.50", "username": "test"}
  ]
}
```

**使用**: 通过 name 指定服务器
```
连接 SSH，name=prod  // 连接生产环境
连接 SSH，name=dev   // 连接开发环境
连接 SSH，name=test  // 连接测试环境
```

---

### 场景 3: 临时连接新服务器

**方式 1: 动态添加**
```
添加 SSH 服务器，name=temp, host=1.2.3.4, username=root
连接 SSH，name=temp
```

**方式 2: 直接参数**
```
连接 SSH，host=1.2.3.4, username=root, password=xxx
```

---

## 🔄 配置更新流程

### 添加新服务器的完整流程

1. **查看当前配置**
   ```
   列出 SSH 服务器
   ```

2. **添加新服务器**
   ```
   添加 SSH 服务器，name=new-server, host=5.6.7.8, username=admin
   ```

3. **验证添加**
   ```
   列出 SSH 服务器
   ```

4. **连接测试**
   ```
   连接 SSH，name=new-server
   执行命令，command=whoami
   ```

---

## ⚠️ 注意事项

### 1. 密码安全
- MCP 配置文件中的密码以环境变量形式存储
- `config/hosts.json` 中的密码会明文显示
- 建议使用 SSH 密钥认证

### 2. 配置优先级
- MCP 配置 > 本地配置 > 用户参数
- 如果 MCP 配置了 `SSH_HOST`，会优先使用
- 想要使用本地配置，需要清空 MCP 配置中的 `SSH_HOST`

### 3. 配置持久化
- MCP 配置：保存在 Trae IDE 配置中
- 本地配置：保存在 `config/hosts.json`
- 参数方式：不保存，仅当前使用

---

## 🎯 最佳实践

1. **主要服务器**: 配置在 MCP 配置文件中
2. **多台服务器**: 配置在 `config/hosts.json` 中
3. **临时连接**: 使用参数方式
4. **定期清理**: 删除不再使用的服务器配置
5. **使用密钥**: 优先使用 SSH 密钥认证

---

**更新时间**: 2026-03-10  
**版本**: ssh-licco 0.1.5
