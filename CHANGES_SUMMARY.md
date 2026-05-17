# SSH-Licco v0.5.2 安全加固

**版本**: v0.5.2  
**日期**: 2026-05-17  
**状态**: 🔒 安全加固提交（待发布）

---

## 🔒 安全改进

### 高风险修复

| # | 漏洞 | 修复文件 | 措施 |
|---|------|----------|------|
| 1 | MITM 攻击（主机密钥绕过） | `session_manager.py` | 替换 `AutoAddPolicy` 为 `RejectPolicy`，默认启用严格主机密钥验证 |
| 2 | 命令注入绕过 | `server.py` | 补全 `ssh_execute_wait`、`ssh_container_logs`、`ssh_docker_status` 的命令验证 |
| 3 | 本地文件路径遍历 | `session_manager.py` | `upload_file`/`download_file` 添加路径验证 |
| 4 | 密码长度信息泄露 | `server.py` | 移除 `ssh_list_hosts` 中的密码长度输出 |

### 中风险修复

| # | 问题 | 修复文件 | 措施 |
|---|------|----------|------|
| 5 | 无会话并发限制 | `session_manager.py` | 添加 `MAX_SESSIONS=10`、`MAX_SESSIONS_PER_HOST=3` 限制 |
| 6 | 线程池资源耗尽 | `executor.py` | `max_workers` 上限从 `CPU*5` 限制为 `min(CPU*5, 20)` |
| 7 | 无敏感操作审计 | `server.py` | 集成 `audit_logger.py`，记录连接/命令/传输事件 |
| 8 | 无频率限制 | `server.py` | 添加滑动窗口 DoS 防护（默认 30次/60秒） |

### 新增安全配置选项

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_SECURITY_LEVEL": "strict",           // strict/balanced/relaxed
        "SSH_RATE_LIMIT": "true",                 // 启用频率限制
        "SSH_RATE_LIMIT_MAX": "30",               // 每窗口最大请求数
        "SSH_RATE_LIMIT_WINDOW": "60",             // 时间窗口（秒）
        "SSH_AUDIT_LOG_PATH": "/var/log/ssh-audit.json",  // 审计日志路径
        "SSH_STRICT_HOST_KEY": "true"              // 严格主机密钥验证
      }
    }
  }
}
```

### 新增 ssh_connect 工具参数

- `strict_host_key_checking` - 启用严格主机密钥验证（默认 True）
- `known_hosts_path` - 指定 known_hosts 文件路径
- `accept_new_host_key` - ⚠️ 危险：自动接受新主机密钥（仅测试用）

---

# SSH-Licco v0.5.0 发布总结

## 🎉 发布成功！

**版本**: v0.5.0  
**日期**: 2026-03-22  
**状态**: ✅ 已发布到 GitHub

---

## 📊 改动统计

### 修改的文件 (6 个)
1. `pyproject.toml` - 版本号升级到 0.5.0
2. `ssh_mcp/connection_config.py` - 认证逻辑优化
3. `ssh_mcp/server.py` - 环境变量支持和 bug 修复
4. `mcp.config.json` - 配置示例更新
5. `config/ssh-hosts.json` - 示例配置
6. `config/hosts.json` - 主机配置

### 新增文件 (2 个)
1. `RELEASE_NOTES_v0.5.0.md` - 详细发布说明
2. `CHANGES_SUMMARY.md` - 改动总结（本文件）

---

## ✨ 核心功能

### 1. Background 参数支持
```python
# 现在支持后台执行命令
await session.execute_command("long-running-task", background=True)
```

### 2. 智能认证检测
```python
# 自动根据提供的凭证选择认证方式
# - 提供密码 → password 认证
# - 提供私钥 → private_key 认证
# - 空字符串密码 → 正确拒绝
```

### 3. 环境变量优先级
```python
# ssh_login 优先使用环境变量
SSH_HOST, SSH_USER, SSH_PASSWORD 等
```

---

## 🔧 关键修复

1. **空字符串密码问题** - 现在会被正确拒绝
2. **Background 参数传递** - 修复了参数未传递的问题
3. **认证逻辑优化** - 提供更清晰的错误提示

---

## 📦 安装方式

```bash
# 升级
pip install --upgrade ssh-licco

# 或重新安装
pip uninstall ssh-licco
pip install ssh-licco
```

---

## 📝 Git 提交

**Commit**: `b04f498`  
**Tag**: `v0.5.0`  
**分支**: `master`  
**远程**: `github.com/Echoqili/ssh-licco`

---

## 🧪 测试状态

✅ 所有测试通过
- Background 参数测试
- 密码认证测试
- 私钥认证测试
- 空密码验证测试
- 环境变量加载测试
- 配置文件加载测试
- 集成测试

---

## 📋 快速使用

### 方式 1: 使用 ssh_login（最简单）
```json
{"tool": "ssh_login", "arguments": {}}
```

### 方式 2: 直接连接
```json
{
  "tool": "ssh_connect",
  "arguments": {
    "host": "192.168.58.130",
    "username": "licco",
    "password": "licco123"
  }
}
```

### 方式 3: 后台执行命令
```json
{
  "tool": "ssh_execute",
  "arguments": {
    "session_id": "xxx",
    "command": "sleep 30 && echo done",
    "background": true
  }
}
```

---

## 🚀 下一步

访问 GitHub 查看完整发布说明：
https://github.com/Echoqili/ssh-licco/releases/tag/v0.5.0

---

**发布完成！🎊**
