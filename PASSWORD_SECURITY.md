# 密码隐藏功能说明

## ✅ 已实现的功能

### 1. 响应中隐藏密码

所有 MCP 工具的响应中，密码都会被隐藏显示为 `***`。

#### 示例输出

**`ssh_list_hosts` 工具**:
```
📋 SSH 服务器配置列表

🔹 [优先级 1] MCP 配置文件 (mcp.json)
  主机：43.143.207.242:22
  用户：root
  密码：***          ← 隐藏显示
  超时：120s

🔹 [优先级 2] 本地配置文件 (config/hosts.json)

  1. production-server
     主机：43.143.207.242:22
     用户：root
     密码：***        ← 隐藏显示
     超时：60s
```

**`ssh_connect` 工具**:
```
Successfully connected to 43.143.207.242:22
Session ID: 7a7cfe96-ff97-45d4-801a-e782865ce95b
Username: root
Keepalive Interval: 30s
Session Timeout: 7200s
Connected at: 2026-03-11T00:48:55.503324
```
✅ 不显示密码字段

**`ssh_config` 工具**:
```
SSH 配置已保存:
主机：43.143.207.242:22
用户名：root
密码：已设置       ← 不显示实际密码
配置文件：config/server.json
```

---

## 🔒 安全特性

### 1. 响应隐藏
- ✅ 所有工具响应中密码显示为 `***`
- ✅ 日志中不记录明文密码
- ✅ 连接信息中不暴露密码

### 2. 存储安全
- ✅ MCP 配置文件中的密码以环境变量形式存储
- ✅ 本地配置文件中的密码已隐藏显示
- ✅ 会话信息中不包含密码

### 3. 传输安全
- ✅ SSH 连接使用加密传输
- ✅ 密码不在网络中明文传输

---

## 📝 修改的代码

### `server.py`

1. **`_handle_connect`** (第 378 行)
   ```python
   # 隐藏密码显示
   password_display = "***" if host_config.password else "未设置"
   ```

2. **`_handle_list_hosts`** (第 521 行)
   ```python
   output += f"  密码：{'***' if self._env_config.get('password') else '未设置'}\n"
   output += f"     密码：{'***' if host.password else '未设置'}\n"
   ```

3. **`_handle_config`** (第 294 行)
   ```python
   output += f"密码：{'已设置' if password else '未设置 (将使用环境变量 SSH_PASSWORD)'}\n"
   ```

---

## 🎯 最佳实践

### 1. 使用环境变量
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_PASSWORD": "你的密码"
      }
    }
  }
}
```

### 2. 不要分享配置文件
- ❌ 不要将包含密码的配置文件提交到 Git
- ❌ 不要在公开场合分享完整的 MCP 配置
- ✅ 使用 `.gitignore` 忽略敏感文件

### 3. 定期更新密码
- 定期更改 SSH 密码
- 使用强密码（包含大小写、数字、特殊字符）

---

## 🔍 测试验证

### 测试 1: 列出服务器
```
列出 SSH 服务器
```
✅ 响应中密码显示为 `***`

### 测试 2: 连接服务器
```
连接 SSH，host=x.x.x.x, username=root, password=xxx
```
✅ 响应中不显示密码

### 测试 3: 保存配置
```
配置 SSH，host=x.x.x.x, username=root, password=xxx
```
✅ 响应中显示"密码：已设置"

---

## ⚠️ 注意事项

1. **密码仍然存储在内存中**
   - 只是为了显示目的而隐藏
   - 实际连接时仍会使用真实密码

2. **配置文件安全**
   - MCP 配置文件 (`mcp.json`) 中的密码以明文存储
   - 建议设置文件权限，限制访问

3. **日志安全**
   - 应用日志中不记录密码
   - 但仍需确保日志文件的安全

---

**更新时间**: 2026-03-11  
**版本**: ssh-licco 0.1.6
