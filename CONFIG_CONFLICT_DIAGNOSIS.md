# SSH 配置冲突诊断工具

## 🔍 问题检测

运行以下命令检查配置冲突：

```bash
# 查看 MCP 配置中的密码
cat mcp.config.json | grep SSH_PASSWORD

# 查看 hosts.json 中的密码
cat config/hosts.json | grep password
```

## 🛠️ Python 诊断脚本

创建一个简单的诊断脚本 `check_config.py`：

```python
#!/usr/bin/env python3
"""SSH 配置冲突检查工具"""

import json
from pathlib import Path

def check_config_conflicts():
    """检查配置冲突"""
    print("=" * 60)
    print("SSH 配置冲突检查工具")
    print("=" * 60)
    
    # 检查 MCP 配置
    mcp_config_path = Path("mcp.config.json")
    if mcp_config_path.exists():
        with open(mcp_config_path, 'r', encoding='utf-8') as f:
            mcp_data = json.load(f)
        
        ssh_env = mcp_data.get("mcpServers", {}).get("ssh-licco", {}).get("env", {})
        if ssh_env:
            print("\n📋 MCP 配置 (mcp.config.json):")
            print(f"  主机：{ssh_env.get('SSH_HOST', '未设置')}")
            print(f"  用户：{ssh_env.get('SSH_USER', '未设置')}")
            print(f"  密码：{'***' if ssh_env.get('SSH_PASSWORD') else '未设置'}")
            print(f"  端口：{ssh_env.get('SSH_PORT', '22')}")
    
    # 检查 hosts.json 配置
    hosts_config_path = Path("config/hosts.json")
    if hosts_config_path.exists():
        with open(hosts_config_path, 'r', encoding='utf-8') as f:
            hosts_data = json.load(f)
        
        ssh_hosts = hosts_data.get("ssh_hosts", [])
        if ssh_hosts:
            print("\n📋 本地配置 (config/hosts.json):")
            for i, host in enumerate(ssh_hosts, 1):
                print(f"\n  服务器 {i}:")
                print(f"    名称：{host.get('name', '未命名')}")
                print(f"    主机：{host.get('host', '未设置')}")
                print(f"    用户：{host.get('username', '未设置')}")
                print(f"    密码：{'***' if host.get('password') else '未设置'}")
                print(f"    端口：{host.get('port', 22)}")
    
    # 检查冲突
    print("\n" + "=" * 60)
    print("冲突检测:")
    print("=" * 60)
    
    if mcp_config_path.exists() and hosts_config_path.exists():
        mcp_host = ssh_env.get('SSH_HOST')
        mcp_user = ssh_env.get('SSH_USER')
        mcp_password = ssh_env.get('SSH_PASSWORD')
        
        for host in ssh_hosts:
            if host.get('host') == mcp_host and host.get('username') == mcp_user:
                if host.get('password') != mcp_password:
                    print(f"\n❌ 发现密码冲突！")
                    print(f"   MCP 配置密码：{mcp_password}")
                    print(f"   hosts.json 密码：{host.get('password')}")
                    print(f"\n💡 建议：统一两个配置文件中的密码")
                    return False
                else:
                    print(f"\n✅ 配置一致，没有冲突")
                    return True
        
        print(f"\n✅ 未检测到相同主机的配置冲突")
        return True
    else:
        print(f"\n⚠️ 配置文件不完整，无法检测冲突")
        return None

if __name__ == "__main__":
    check_config_conflicts()
```

使用方法：

```bash
# 运行诊断
python check_config.py
```

## 🎯 解决方案

### 方案 1：统一密码（推荐）

确保 `mcp.config.json` 和 `config/hosts.json` 中的密码一致：

**mcp.config.json:**
```json
{
  "env": {
    "SSH_PASSWORD": "licco123"
  }
}
```

**config/hosts.json:**
```json
{
  "ssh_hosts": [
    {
      "name": "openmaic-server",
      "host": "192.168.58.130",
      "username": "licco",
      "password": "licco123"
    }
  ]
}
```

### 方案 2：只使用一种配置方式

#### 选项 A：仅使用 MCP 环境变量（推荐用于生产环境）

1. 在 `mcp.config.json` 中配置：
```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "licco123",
        "SSH_PORT": "22"
      }
    }
  }
}
```

2. 删除或清空 `config/hosts.json`（或将其密码设为空字符串）

#### 选项 B：仅使用配置文件（推荐用于开发环境）

1. 在 `config/hosts.json` 中配置完整信息
2. 在 `mcp.config.json` 中不设置 SSH 相关环境变量

### 方案 3：使用 SSH_FORCE_ENV_CONFIG 强制模式

在生产环境中，强制使用环境变量配置：

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.58.130",
        "SSH_USER": "licco",
        "SSH_PASSWORD": "licco123",
        "SSH_FORCE_ENV_CONFIG": "true"
      }
    }
  }
}
```

这将确保始终使用环境变量中的配置，忽略配置文件。

## 📋 最佳实践清单

- [ ] **统一密码**：确保所有配置文件中的密码一致
- [ ] **使用密钥认证**：优先使用 SSH 密钥代替密码
- [ ] **版本控制**：不要将密码提交到 Git
- [ ] **环境隔离**：开发、测试、生产环境使用不同的配置
- [ ] **定期审查**：定期检查配置文件是否有冲突
- [ ] **文档化**：记录配置优先级和使用方法

## 🔧 快速修复步骤

1. **确定正确的密码**
   - 测试哪个密码可以成功登录
   - 询问团队成员正确的密码

2. **更新配置文件**
   ```bash
   # 更新 hosts.json
   # 手动编辑 config/hosts.json，确保密码正确
   ```

3. **验证配置**
   ```bash
   python check_config.py
   ```

4. **测试连接**
   ```python
   # 在 Trae IDE 中执行
   ssh_login()
   ```

## 📖 相关文档

- [连接优先级配置指南](./CONNECTION_PRIORITY_MODES.md)
- [SSH 配置最佳实践](./docs/SSH_BEST_PRACTICES.md)
- [本地安装指南](./docs/skills/ssh-mcp-setup/SKILL.md)
