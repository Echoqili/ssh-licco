# SSH MCP 本地安装成功指南

## ✅ 安装状态

**ssh-licco 0.1.5** 已成功安装到本地环境！

### 安装信息

- **版本**: 0.1.5
- **安装方式**: 可编辑模式（`pip install -e . --user`）
- **安装位置**: `C:\Users\Administrator\AppData\Roaming\Python\Python313\site-packages`
- **项目位置**: `D:\pyworkplace\ssh-mcp`
- **Python 版本**: 3.13

### 已验证功能

✅ SSH MCP 模块导入成功  
✅ SSHMCPServer 类可用  
✅ 所有依赖已正确安装  

## 🚀 使用方法

### 1. 配置环境变量（推荐）

为了避免密码泄露，建议使用环境变量：

```powershell
# PowerShell
$env:SSH_PASSWORD="你的密码"
```

或者永久设置（添加到系统环境变量）：
1. 右键"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 在"用户变量"或"系统变量"中添加：
   - 变量名：`SSH_PASSWORD`
   - 变量值：`你的密码`

### 2. 配置 SSH 主机

编辑 `config/hosts.json`：

```json
{
  "ssh_hosts": [
    {
      "name": "我的服务器",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "",  // 留空，使用环境变量
      "timeout": 120,
      "banner_timeout": 120,
      "keepalive_interval": 30,
      "session_timeout": 7200
    }
  ]
}
```

### 3. 作为 MCP 服务器运行

在 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco"
    }
  }
}
```

### 4. 直接运行（测试用）

```bash
# 使用环境变量
$env:SSH_HOST="43.143.207.242"
$env:SSH_PORT="22"
$env:SSH_USER="root"
$env:SSH_PASSWORD="你的密码"

# 运行服务器
ssh-licco
```

## 📝 可用工具

安装后，MCP 客户端可以使用以下工具：

1. **ssh_config** - 配置 SSH 连接参数
2. **ssh_login** - 使用保存的配置登录
3. **ssh_connect** - 建立 SSH 连接
4. **ssh_list_hosts** - 列出配置的主机
5. **ssh_execute** - 执行命令
6. **ssh_disconnect** - 断开连接
7. **ssh_list_sessions** - 列出活动会话
8. **ssh_generate_key** - 生成 SSH 密钥对
9. **ssh_file_transfer** - 文件传输（SFTP）
10. **ssh_background_task** - 后台执行长任务
11. **ssh_task_status** - 查看后台任务状态
12. **ssh_docker_build** - Docker 构建
13. **ssh_docker_status** - Docker 状态查询

## 🔧 安全改进

本次安装包含以下安全增强：

### 1. 环境变量支持
- 密码通过 `SSH_PASSWORD` 环境变量读取
- 不会在配置文件或日志中显示明文密码

### 2. 超时优化
- 增加了 `banner_timeout` 配置（默认 120 秒）
- 解决 "Error reading SSH protocol banner" 问题

### 3. 密码隐藏
- 配置输出显示 "已设置" 而非实际密码
- 日志中不暴露敏感信息

## 📚 相关文档

- [安全配置指南](SECURITY_GUIDE.md) - 详细的安全配置说明
- [README.md](README.md) - 项目说明
- [USAGE.md](USAGE.md) - 使用指南

## ⚠️ 注意事项

### PATH 警告

安装时出现警告：
```
The script ssh-licco.exe is installed in 'C:\Users\Administrator\AppData\Roaming\Python\Python313\Scripts' 
which is not on PATH.
```

**解决方案**（可选）：

1. **添加到 PATH**：
   ```powershell
   $env:Path += ";C:\Users\Administrator\AppData\Roaming\Python\Python313\Scripts"
   ```

2. **或者直接使用完整路径**：
   ```
   C:\Users\Administrator\AppData\Roaming\Python\Python313\Scripts\ssh-licco.exe
   ```

3. **或者在 MCP 配置中指定完整路径**：
   ```json
   {
     "mcpServers": {
       "ssh-licco": {
         "command": "C:\\Users\\Administrator\\AppData\\Roaming\\Python\\Python313\\Scripts\\ssh-licco.exe"
       }
     }
   }
   ```

## 🧪 快速测试

```powershell
# 1. 设置环境变量
$env:SSH_PASSWORD="你的密码"

# 2. 验证模块导入
python -c "from ssh_mcp.server import SSHMCPServer; print('✅ 模块加载成功')"

# 3. 检查安装
pip show ssh-licco
```

## 📞 需要帮助？

如果遇到问题：

1. 检查 [SECURITY_GUIDE.md](SECURITY_GUIDE.md) 了解安全配置
2. 查看项目文档了解详细用法
3. 检查日志文件排查问题

---

**安装时间**: 2026-03-10  
**安装版本**: ssh-licco 0.1.5  
**安装状态**: ✅ 成功
