# MCP 配置指南

## ✅ 已完成

1. **SSH-licco 已安装**: `pip install -e . --user` ✅
2. **环境变量已配置** (在你的 MCP 配置中) ✅

## 📝 手动配置步骤

### 步骤 1: 打开 MCP 配置文件

在 Trae IDE 中，MCP 配置文件位于：
```
C:\Users\Administrator\AppData\Roaming\Trae\User\mcp.json
```

### 步骤 2: 添加 SSH 配置

打开文件后，在 `mcpServers` 对象中添加以下配置：

```json
"ssh": {
  "command": "ssh-licco",
  "env": {
    "SSH_HOST": "43.143.207.242",
    "SSH_USER": "root",
    "SSH_PASSWORD": "P/[KY}+wa7?2|uc",
    "SSH_PORT": "22",
    "SSH_TIMEOUT": "120",
    "SSH_KEEPALIVE_INTERVAL": "30",
    "SSH_SESSION_TIMEOUT": "7200"
  }
}
```

### 步骤 3: 完整配置示例

修改后的 `mcp.json` 应该如下所示：

```json
{
  "mcpServers": {
    "GitHub": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }
    },
    "Gitee": {
      "command": "mcp-gitee",
      "args": [
        "--transport",
        "sse",
        "--sse-address",
        "0.0.0.0:8000"
      ],
      "env": {
        "GITEE_ACCESS_TOKEN": "your_token",
        "GITEE_API_BASE": "https://gitee.com/api/v5"
      }
    },
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "43.143.207.242",
        "SSH_USER": "root",
        "SSH_PASSWORD": "P/[KY}+wa7?2|uc",
        "SSH_PORT": "22",
        "SSH_TIMEOUT": "120",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200"
      }
    }
  }
}
```

### 步骤 4: 保存并重启

1. 保存 `mcp.json` 文件
2. 重启 Trae IDE 或重新加载窗口
3. 检查 MCP 服务器状态

### 步骤 5: 验证配置

在 Trae IDE 中：
1. 打开 MCP 面板（通常在侧边栏）
2. 查看 "ssh" 服务器是否在线
3. 尝试使用 SSH 工具：
   - `ssh_list_hosts` - 列出主机
   - `ssh_connect` - 连接服务器
   - `ssh_execute` - 执行命令

## ⚠️ 注意事项

### 1. SSH 服务器问题

**重要**: 当前 SSH 服务器 (43.143.207.242) 的 SSH 服务可能有问题。

如果连接失败，请检查：
- 服务器 SSH 服务是否正常运行
- 防火墙设置
- 安全组规则

参考：[CONNECTION_TEST_REPORT.md](CONNECTION_TEST_REPORT.md)

### 2. 密码安全

当前配置使用了明文密码。建议：
- 使用 SSH 密钥认证（更安全）
- 不要将配置文件提交到版本控制

### 3. 超时设置

已将超时时间增加到 120 秒，以解决网络延迟问题：
- `SSH_TIMEOUT`: 120
- `SSH_KEEPALIVE_INTERVAL`: 30
- `SSH_SESSION_TIMEOUT`: 7200

## 🔧 故障排查

### 问题 1: MCP 服务器未启动

**症状**: Trae IDE 中看不到 ssh 服务器

**解决**:
1. 检查 `mcp.json` 语法是否正确
2. 重启 Trae IDE
3. 检查日志：`ssh-licco` 是否有错误输出

### 问题 2: 连接超时

**症状**: `Error reading SSH protocol banner`

**解决**:
1. 检查服务器 SSH 服务状态
2. 通过云控制台登录服务器
3. 重启 SSH: `sudo systemctl restart sshd`

### 问题 3: 认证失败

**症状**: `Authentication failed`

**解决**:
1. 检查密码是否正确
2. 检查用户名是否正确
3. 考虑使用 SSH 密钥认证

## 📞 需要帮助？

如果配置后仍无法使用：

1. 检查 [TOOL_DIAGNOSE_REPORT.md](TOOL_DIAGNOSE_REPORT.md) - 工具诊断
2. 检查 [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 安全配置
3. 查看 Trae IDE 的 MCP 日志

---

**配置创建时间**: 2026-03-10  
**配置版本**: ssh-licco 0.1.5
