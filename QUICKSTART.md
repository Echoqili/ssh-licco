# 🚀 ssh-licco 快速开始指南

## 一分钟快速上手

### 1. 创建项目配置

在你的项目根目录创建 `mcp.config.json` 文件：

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "your-server-ip",
        "SSH_USER": "your-username",
        "SSH_PASSWORD": "your-password",
        "SSH_PORT": "22",
        "SSH_SECURITY_LEVEL": "balanced"
      }
    }
  }
}
```

### 2. 启动使用

#### 方式 A：npx 一键启动（推荐，零配置）

```bash
npx ssh-licco
```

首次运行自动完成：检测 Python → 创建虚拟环境 → 安装依赖 → 验证完整性 → 启动 MCP 服务器。

#### 方式 B：pip 安装后直接运行

```bash
pip install ssh-licco
ssh-licco
```

#### 方式 C：智能安装脚本（适合首次使用）

```bash
python smart_install.py
```

### 3. 开始使用

在你的 MCP 客户端（Trae/Cursor/Claude Desktop）中配置好 `mcp.config.json` 后，重启客户端即可使用！

---

## 🏗️ 自动安装体系

ssh-licco 采用三层架构实现零配置启动：

```
npx ssh-licco
     ↓
ssh-licco.js (Node 层)
  ├─ ① 查找 Python 3.10+
  ├─ ② 检测 Anaconda 环境
  ├─ ③ 创建/复用 ~/.ssh-licco-venv
  ├─ ④ pip install -e . 安装依赖
  ├─ ⑤ 验证依赖完整性
  └─ ⑥ 启动 Python MCP 服务器
     ↓
cli.py → SSHMCPServer (MCP 服务)
```

### 智能安装特性

| 特性 | 说明 |
|------|------|
| **自我修复** | 每次启动验证依赖完整性，缺失则自动修复 |
| **增量更新** | 已有 venv 时不删除重建，直接增量安装 |
| **Anaconda 兼容** | 自动检测 conda 环境，使用独立 venv 避免冲突（[详细说明](./ANACONDA_GUIDE.md)） |
| **即开即用** | 连 `npm install` 都不需要，`npx` 直接启动 |

---

## 智能安装详解

### 🔧 启动流程

```
1. 用户执行 npx ssh-licco
           ↓
2. ssh-licco.js (Node.js 包装器)
   ├─ 查找可用的 Python 3.10+
   ├─ 检测 Anaconda 环境（给出提示）
   ├─ 检查 ~/.ssh-licco-venv 是否存在
   │   ├─ 不存在 → python -m venv 创建
   │   └─ 存在 → 跳过
   ├─ 检查依赖完整性
   │   ├─ 完整 → 直接启动
   │   └─ 损坏 → 自动 pip install 修复
   └─ 启动 Python MCP 服务器
           ↓
3. cli.py (Python 入口)
   └─ 启动 SSHMCPServer
           ↓
4. MCP 服务就绪，等待客户端连接
```

### 📦 文件说明

| 文件 | 作用 |
|------|------|
| [ssh-licco.js](ssh-licco.js) | Node.js 包装器，负责环境准备和启动 |
| [install.js](install.js) | npm postinstall 脚本，增量更新安装 |
| [smart_install.py](smart_install.py) | 独立安装诊断脚本，可单独运行 |
| [cli.py](ssh_mcp/cli.py) | Python 入口，只负责启动 MCP 服务器 |

---

## 🔧 配置选项

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SSH_LICCO_AUTO_INSTALL` | `true` | 启用/禁用自动安装 |
| `SSH_HOST` | - | SSH 服务器地址 |
| `SSH_USER` | - | SSH 用户名 |
| `SSH_PASSWORD` | - | SSH 密码 |
| `SSH_PORT` | `22` | SSH 端口 |
| `SSH_SECURITY_LEVEL` | `balanced` | 安全级别 (`strict`/`balanced`/`relaxed`) |
| `SSH_TIMEOUT` | `60` | 连接超时（秒） |
| `SSH_KEEPALIVE_INTERVAL` | `30` | 保活间隔（秒） |
| `SSH_SESSION_TIMEOUT` | `7200` | 会话超时（秒） |
| `SSH_CLIENT_TYPE` | `paramiko` | SSH 客户端类型（`common`/`performance`/`development`） |
| `SSH_EXTRA_ALLOWED_COMMANDS` | - | 额外允许的命令（逗号分隔） |
| `SSH_BASE_DIR` | `/home` | 允许的基础目录 |

---

## 🖥️ CLI 命令行

除了 MCP 服务器模式，ssh-licco 还提供命令行工具：

```bash
# 执行远程命令
ssh-licco exec --host 192.168.1.100 -u root --password pwd "ls -la"

# 上传文件
ssh-licco upload --host 192.168.1.100 -u root --password pwd ./file.txt /remote/file.txt

# 下载文件
ssh-licco download --host 192.168.1.100 -u root --password pwd /remote/file.txt ./file.txt

# 远程 Docker 构建
ssh-licco docker-build --host 192.168.1.100 -u root --password pwd myapp:latest

# 列出已配置主机
ssh-licco list-hosts
```

> 💡 使用环境变量后可省略 `--host`、`-u`、`--password` 参数。

---

## ⚠️ 常见问题

### Q: 启动报 `Cannot find module` 错误？
```bash
npm uninstall -g ssh-licco
# 卸载全局损坏包，然后重试
```

### Q: 依赖不全或启动报模块找不到？
ssh-licco 每次启动会自动验证依赖完整性并修复。也可以手动运行：
```bash
node install.js
```

### Q: 想全新重装？
```bash
rm -rf ~/.ssh-licco-venv
npx ssh-licco
```

---

## 📚 更多文档

- [完整 README](./README.md)
- [使用指南](./USAGE.md)
- [安全配置](./SECURITY_CONFIG_GUIDE.md)
- [Anaconda 环境指南](./ANACONDA_GUIDE.md)
- [Skills 文档](./docs/skills/)