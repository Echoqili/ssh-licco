# Anaconda/Miniconda 环境指南

本指南说明如何在 Anaconda/Miniconda 环境中安全使用 ssh-licco，避免与系统 Python 或其他 conda 环境发生冲突。

## 🔒 自动冲突检测

ssh-licco 安装器具有自动 Anaconda 检测功能：

- ✅ 自动检测当前是否在 conda 环境中
- ✅ 自动检测 Python 是否来自 Anaconda/Miniconda
- ✅ 提供隔离的安装方式，避免破坏现有环境
- ✅ 给出清晰的提示信息

## 📦 安装方式

### 方式1: npm 安装（推荐，完全隔离）

npm 版本的 ssh-licco 会创建独立的虚拟环境，与 conda 完全隔离：

```bash
# 在项目中安装
npm install ssh-licco --save-dev

# 或者全局安装
npm install -g ssh-licco
```

**工作原理：**
1. npm 安装器会创建独立的 `~/.ssh-licco-venv` 虚拟环境
2. 不会干扰任何 conda 环境
3. 自动检测合适的 Python 解释器

### 方式2: pip 安装（在当前 conda 环境中）

如果你希望在特定的 conda 环境中使用 ssh-licco：

```bash
# 激活目标 conda 环境
conda activate myenv

# 在该环境中安装
pip install ssh-licco
```

### 方式3: 智能安装脚本

```bash
# 克隆项目
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco

# 运行智能安装（自动检测环境）
python smart_install.py
```

## 🛠️ 配置 mcp.config.json

### npm 版本配置

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "npx",
      "args": ["ssh-licco"],
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "your-server",
        "SSH_USER": "your-user",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

### pip 版本配置（在 conda 环境中）

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "/path/to/your/conda/env/bin/ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "false",
        "SSH_HOST": "your-server",
        "SSH_USER": "your-user",
        "SSH_PASSWORD": "your-password"
      }
    }
  }
}
```

## 🔍 环境诊断

安装时自动显示的诊断信息：

```
============================================================
🚀 ssh-licco Installer
============================================================
🔍 Diagnosing Python environment...
  • Platform: Windows-10-10.0.19045-SP0
  • Home directory: C:\Users\YourName
  ⚠️  Found python: Python 3.11.5 (Anaconda - will use isolated venv)

📦 Package path: C:\path\to\ssh-licco
🌐 Virtual environment: C:\Users\YourName\.ssh-licco-venv

🔧 Creating isolated virtual environment...
   This ensures no conflicts with your Anaconda installation
   ✅ Virtual environment created successfully
```

## ⚠️ 常见问题

### Q: 安装时会修改我的 conda 环境吗？

**A:** 不会！
- npm 版本使用独立的虚拟环境，完全隔离
- pip 版本只在当前激活的 conda 环境中安装
- 不会影响其他 conda 环境或系统 Python

### Q: 我有多个 conda 环境，应该用哪个？

**A:** 推荐方式：
1. 使用 npm 版本（最简单，完全隔离）
2. 或者选择一个常用的 conda 环境安装 pip 版本

### Q: 可以在 base 环境中安装吗？

**A:** 可以，但推荐：
- npm 版本：完全隔离，最安全
- pip 版本：可以在 base 环境安装，但建议创建专用环境

### Q: 如何卸载？

**A:** 
- npm 版本：`npm uninstall -g ssh-licco`，然后删除 `~/.ssh-licco-venv`
- pip 版本：`pip uninstall ssh-licco`

## 📝 最佳实践

1. **首选 npm 版本**：完全隔离，无需管理 Python 环境
2. **使用智能安装**：`python smart_install.py` 自动处理
3. **配置文件管理**：将 `mcp.config.json` 放在项目目录中
4. **环境变量**：敏感信息使用环境变量，不要硬编码

## 🔧 故障排除

### 问题: 找不到 Python 解释器

**解决:**
1. 安装 Python 3.10+ 从 python.org
2. 确保安装时勾选 "Add Python to PATH"
3. 或者在 conda 环境中使用 pip 版本

### 问题: 权限错误

**解决:**
- npm 版本：不需要管理员权限
- pip 版本：使用 `--user` 标志或在虚拟环境中安装

### 问题: 多个 Python 版本冲突

**解决:**
- npm 版本自动选择合适的 Python
- pip 版本确保在正确的 conda 环境中

## 📚 更多资源

- [快速开始指南](./QUICKSTART.md)
- [完整 README](./README.md)
- [安全配置](./SECURITY_CONFIG_GUIDE.md)
