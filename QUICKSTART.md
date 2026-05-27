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

### 2. 智能安装

#### 方式 A：使用 npm（推荐 Node.js 项目）

```bash
# 在项目目录中安装
npm install ssh-licco --save-dev

# 或者直接运行智能安装脚本
npx ssh-licco
```

#### 方式 B：使用 pip（推荐 Python 项目）

```bash
# 使用智能安装脚本
python smart_install.py

# 或者直接安装
pip install ssh-licco
```

### 3. 开始使用

在你的 MCP 客户端（Trae/Cursor/Claude Desktop）中配置好 `mcp.config.json` 后，重启客户端即可使用！

---

## 智能安装特性

### ✨ 自动检测与安装

- 自动检测 `mcp.config.json` 配置文件
- 如果未安装，自动执行安装
- 支持从源码或 PyPI 安装
- 安装后自动验证

### 🔧 配置选项

#### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SSH_LICCO_AUTO_INSTALL` | `true` | 启用/禁用自动安装 |
| `SSH_HOST` | - | SSH 服务器地址 |
| `SSH_USER` | - | SSH 用户名 |
| `SSH_PASSWORD` | - | SSH 密码 |
| `SSH_PORT` | `22` | SSH 端口 |
| `SSH_SECURITY_LEVEL` | `balanced` | 安全级别 (`strict`/`balanced`/`relaxed`) |

---

## 使用场景示例

### 场景 1：Web 开发项目

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "deploy",
        "SSH_PASSWORD": "your-secure-password",
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "git,npm,docker"
      }
    }
  }
}
```

### 场景 2：数据科学项目

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "gpu-server.example.com",
        "SSH_USER": "datascience",
        "SSH_PASSWORD": "your-secure-password",
        "SSH_SECURITY_LEVEL": "relaxed",
        "SSH_EXTRA_ALLOWED_COMMANDS": "python,pip,jupyter,docker"
      }
    }
  }
}
```

---

## 一键安装命令

### 快速安装脚本

```bash
# Python 项目
curl -sSL https://raw.githubusercontent.com/Echoqili/ssh-licco/main/smart_install.py | python

# Node.js 项目
npm install ssh-licco
```

### 或者使用本地脚本

```bash
# 克隆仓库
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco

# 运行智能安装
python smart_install.py
```

---

## 🎯 最佳实践

### 1. 项目级安装（推荐）

在每个项目中独立安装 ssh-licco，这样可以：
- 避免版本冲突
- 便于团队协作
- 配置文件与代码一起管理

### 2. 使用环境变量

不要在代码中硬编码密码，使用环境变量：

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "${SSH_HOST}",
        "SSH_USER": "${SSH_USER}",
        "SSH_PASSWORD": "${SSH_PASSWORD}"
      }
    }
  }
}
```

### 3. 版本锁定

在 `package.json` 或 `requirements.txt` 中锁定版本：

```json
{
  "devDependencies": {
    "ssh-licco": "^0.5.0"
  }
}
```

---

## 📚 更多文档

- [完整 README](./README.md)
- [配置指南](./MCP_CONFIG_GUIDE.md)
- [安全配置](./SECURITY_CONFIG_GUIDE.md)
- [Anaconda/Miniconda 环境指南](./ANACONDA_GUIDE.md) - 使用 conda 时必读
- [Skills 文档](./docs/skills/)
