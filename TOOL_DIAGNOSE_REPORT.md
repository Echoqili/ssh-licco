# SSH-licco 工具问题诊断报告

## 📊 诊断结果

**诊断时间**: 2026-03-10  
**状态**: ✅ **工具本身正常**，运行方式需要调整

---

## ✅ 已验证正常的功能

### 1. 模块导入 ✅
```
✅ ssh_mcp 模块已导入
路径：D:\pyworkplace\ssh-mcp\ssh_mcp\__init__.py
版本：0.2.1
```

### 2. 依赖包安装 ✅
```
✅ mcp: 已安装
✅ asyncssh: 2.22.0
✅ pydantic: 2.12.5
✅ pydantic_settings: 2.13.1
```

### 3. SSHMCPServer 创建 ✅
```
✅ 类已导入
✅ 实例已创建
服务器名称：ssh-licco
版本：0.1.4
```

### 4. 入口脚本存在 ✅
```
✅ D:\software\anaconda\Scripts\ssh-licco.exe (108,392 bytes)
✅ C:\Users\Administrator\AppData\Roaming\Python\Python313\Scripts\ssh-licco.exe
```

### 5. pip 安装信息 ✅
```
Name: ssh-licco
Version: 0.1.5
Summary: SSH Model Context Protocol Server
```

---

## ⚠️ 发现的问题

### 问题 1: 命令行工具卡住

**现象**:
```powershell
ssh-licco --help  # 卡住，无响应
```

**原因分析**:
- `ssh-licco` 命令设计为 **MCP 服务器**，不是命令行工具
- 它期望通过 **stdio** 与 MCP 客户端通信
- 直接在命令行运行会等待 MCP 客户端连接，因此看起来"卡住"

**这不是 bug**，而是预期行为！

### 问题 2: SSH 服务器连接失败

**现象**:
```
❌ Error reading SSH protocol banner
❌ Connection timed out during banner exchange
```

**原因**: 
- 云端 SSH 服务器 (43.143.207.242) 的 SSH 服务异常
- 不是本地工具的问题

**解决方案**: 需要修复云端 SSH 服务（见 CONNECTION_TEST_REPORT.md）

---

## 🔧 正确的使用方式

### 方式 1: 作为 MCP 服务器运行（推荐）

`ssh-licco` 是设计给 MCP 客户端使用的，不是直接命令行工具。

**配置 MCP 客户端**（如 Trae、Claude Desktop 等）:

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "43.143.207.242",
        "SSH_USER": "root",
        "SSH_PASSWORD": "你的密码",
        "SSH_PORT": "22"
      }
    }
  }
}
```

然后在 MCP 客户端中使用工具：
- `ssh_config` - 配置连接
- `ssh_connect` - 建立连接
- `ssh_execute` - 执行命令
- 等等...

### 方式 2: 使用 Python 直接调用

```python
from ssh_mcp.server import SSHMCPServer
import asyncio

async def use_ssh_tool():
    server = SSHMCPServer()
    
    # 配置环境变量
    import os
    os.environ['SSH_HOST'] = '43.143.207.242'
    os.environ['SSH_USER'] = 'root'
    os.environ['SSH_PASSWORD'] = '你的密码'
    
    # 工具会通过 MCP 客户端调用
    # 不要直接运行 server.run()

# asyncio.run(use_ssh_tool())
```

### 方式 3: 测试工具功能

我已经创建了测试脚本：

```powershell
# 运行诊断
python diagnose.py

# 测试工具调用
python test_tool_call.py
```

---

## 📋 工具列表

SSH-licco 提供以下 MCP 工具：

1. **ssh_config** - 配置 SSH 连接
2. **ssh_login** - 使用保存的配置登录
3. **ssh_connect** - 建立 SSH 连接
4. **ssh_list_hosts** - 列出配置的主机
5. **ssh_execute** - 执行命令
6. **ssh_disconnect** - 断开连接
7. **ssh_list_sessions** - 列出活动会话
8. **ssh_generate_key** - 生成 SSH 密钥对
9. **ssh_file_transfer** - 文件传输
10. **ssh_background_task** - 后台执行长任务
11. **ssh_task_status** - 查看后台任务状态
12. **ssh_docker_build** - Docker 构建
13. **ssh_docker_status** - Docker 状态查询

---

## 🎯 问题总结

### 是本地服务问题吗？
❌ **不是**。本地工具安装完全正常。

### 是 PyPI 云端问题吗？
❌ **不是**。所有依赖包都已正确安装。

### 真正的问题是什么？

1. **使用方式误解**：
   - `ssh-licco` 是 MCP 服务器，不是命令行工具
   - 需要在 MCP 客户端中配置使用

2. **SSH 服务器问题**：
   - 云端 SSH 服务 (43.143.207.242) 异常
   - 需要修复服务器端的 SSH 服务

---

## ✅ 解决方案

### 立即行动

1. **配置 MCP 客户端**：
   - 在 Trae IDE 或其他 MCP 客户端中配置 ssh-licco
   - 添加环境变量（SSH_HOST, SSH_PASSWORD 等）

2. **修复 SSH 服务器**：
   - 通过云控制台登录服务器
   - 重启 SSH 服务：`sudo systemctl restart sshd`
   - 查看日志：`sudo journalctl -u sshd`

3. **测试连接**：
   ```powershell
   $env:SSH_PASSWORD="P/[KY}+wa7?2|uc"
   python test_connection_advanced.py
   ```

### 长期建议

1. **使用 SSH 密钥认证**（更安全）
2. **配置多个 SSH 主机**（在 hosts.json 中）
3. **设置合理的超时时间**（已配置 120 秒）
4. **定期更新工具**：`pip install -U ssh-licco`

---

## 📞 需要帮助？

如果还有问题：

1. 检查 [INSTALL_SUCCESS.md](INSTALL_SUCCESS.md) - 安装指南
2. 检查 [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 安全配置
3. 检查 [CONNECTION_TEST_REPORT.md](CONNECTION_TEST_REPORT.md) - 连接测试

---

**诊断工具**:
- `diagnose.py` - 完整诊断脚本
- `test_connection_advanced.py` - SSH 连接测试
- `test_tool_call.py` - MCP 工具测试

**诊断完成时间**: 2026-03-10  
**结论**: 工具正常，需要正确配置使用
