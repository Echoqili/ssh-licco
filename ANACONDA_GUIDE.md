# Anaconda/Miniconda 环境指南

本指南说明如何在 Anaconda/Miniconda 环境中安全使用 ssh-licco，避免环境冲突。

---

## 目录
1. [三层防污染架构](#-三层防污染架构)
2. [PATH 配置建议](#-path-配置建议)
3. [安装方式](#-安装方式)
4. [MCP 配置](#-配置-mcpjson)
5. [环境诊断](#-环境诊断)
6. [常见问题](#-常见问题)
7. [最佳实践](#-最佳实践)

---

## 🏗️ 三层防污染架构

ssh-licco 通过 **三层隔离架构** 保证与 Anaconda 环境完全隔离：

```
用户执行: npx ssh-licco 或 ssh-licco
        │
        ▼
┌─ Layer 1: 入口隔离 ──────────────────────┐
│  npm 包装器 (ssh-licco.js)                │
│  ├─ checkGlobalCommand()                  │
│  │  检测 ssh-licco 命令是否被 Anaconda    │
│  │  抢占了（多个入口点报警）               │
│  └─ diagnosePythonEnvironment()           │
│     按优先级找 Python 3.10+：              │
│      ① 独立安装路径 (AppData\Python)       │
│      ② PATH 上的非 Anaconda Python       │
│      ③ Anaconda（最后手段，醒目警告）     │
└───────────────────────────────────────────┘
        │ spawn(sshLicco, { stdio: 'inherit' })
        ▼
┌─ Layer 2: 虚拟环境隔离 ──────────────────┐
│  ~/.ssh-licco-venv                        │
│  ├─ 独立的 python.exe                     │
│  ├─ 独立的 pip.exe                        │
│  └─ 独立的 ssh-licco.exe 入口             │
│    与 Anaconda 完全无关                   │
└───────────────────────────────────────────┘
        │
        ▼
┌─ Layer 3: 运行时隔离 ────────────────────┐
│  verifyIntegrity() 每次启动校验：          │
│  ├─ venv 目录存在                         │
│  ├─ Python 可执行                         │
│  ├─ ssh_licco 模块可导入                  │
│  └─ 不完整则自动修复 (autoInstall)         │
└───────────────────────────────────────────┘
        │
        ▼
   MCP Server (stdio) → IDE 调用
```

### 各层详解

**第 1 层 — 入口隔离**

当用户执行 `ssh-licco` 命令时，系统通过 PATH 环境变量找到入口。npm 全局安装的包装器 (`ssh-licco.cmd`) 会：
1. 调用 `where ssh-licco` 检查是否存在多个入口点
2. 如果 Anaconda 的入口点优先级高于 npm 全局，发出警告
3. 按优先级顺序寻找 Python 3.10+，优先使用独立安装的 Python

**第 2 层 — 虚拟环境隔离**

即使只有 Anaconda 的 Python 可用，创建的 venv 也是完全独立的：

```
# 创建阶段 - 可能用到 Anaconda 的 python.exe
Anaconda\python.exe -m venv ~/.ssh-licco-venv

# 运行阶段 - 完全独立
~/.ssh-licco-venv\Scripts\python.exe    # ← 自己的 Python
~/.ssh-licco-venv\Scripts\pip.exe       # ← 自己的 pip
~/.ssh-licco-venv\Scripts\ssh-licco.exe # ← 自己的入口
```

**第 3 层 — 运行时完整性校验**

每次启动时，npm 包装器会校验 venv 完整性：

```javascript
// 伪代码逻辑
if (!exists(venv/python.exe))      → autoInstall()
if (!canImport(ssh_mcp.server))    → autoInstall(true) // 强制重装
if (checkAnaconda(pathPython))     → 使用独立 venv + 醒目警告
```

---

## 🔧 PATH 配置建议

### 为什么 PATH 顺序很重要

当你在终端执行 `ssh-licco` 时，系统按 PATH 中的目录顺序查找可执行文件。如果 Anaconda 的目录排在 npm 全局目录前面，就会启动 Anaconda 安装的版本而非 npm 版本。

### 检查当前 PATH

```powershell
# 查看 PATH 中所有目录（按顺序）
$env:Path -split ';'

# 查看 ssh-licco 命令从哪个路径解析
where ssh-licco
```

### 确保 npm 全局优先

```powershell
# 查看 npm 全局安装目录
npm config get prefix
# 输出示例: D:\software\nodejs\node_global

# 查看 Anaconda 目录（通常在 Scripts 子目录）
# 例如: D:\software\anaconda\Scripts
```

在 **系统环境变量** 中调整 PATH，将 npm 全局目录移到 Anaconda 目录之前：

```
正确的顺序:
  D:\software\nodejs\node_global          ← npm 全局（优先）
  D:\software\anaconda\Scripts            ← Anaconda（靠后）
  D:\software\anaconda                    ← Anaconda（靠后）
```

### 验证配置

```powershell
# 重启终端后验证
Get-Command ssh-licco
# 期望输出: D:\software\nodejs\node_global\ssh-licco
# 不应输出: D:\software\anaconda\Scripts\ssh-licco

# 如果仍有问题，清理残留的 Anaconda 入口
Remove-Item "D:\software\anaconda\Scripts\ssh-licco.exe" -Force
Remove-Item "D:\software\anaconda\Scripts\ssh-licco-script.py" -Force
```

### 多个安装来源诊断

ssh-licco 的入口包装器会自动检测并报告多个安装来源：

```
⚠️  Multiple ssh-licco installations found:
     D:\software\nodejs\node_global\ssh-licco       # npm 全局（正确）
     D:\software\nodejs\node_global\ssh-licco.cmd   # npm 全局（正确）
     C:\Users\Admin\.ssh-licco-venv\Scripts\ssh-licco.exe  # 独立 venv（正确）
     D:\software\anaconda\Scripts\ssh-licco.exe     # Anaconda（需清理）
```

---

## 📦 安装方式

### 方式 1: npm 安装（推荐，完全隔离）

```bash
# 全局安装
npm install -g ssh-licco

# 或在项目中安装
npm install ssh-licco --save-dev
```

### 方式 2: pip 安装（在 conda 环境中）

```bash
# 激活目标 conda 环境
conda activate myenv

# 在该环境中安装
pip install ssh-licco
```

---

## ⚙️ 配置 mcp.json

### npm 版本配置

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "ssh-licco",
      "env": {
        "SSH_LICCO_AUTO_INSTALL": "true",
        "SSH_HOST": "your-server",
        "SSH_USER": "your-user",
        "SSH_PASSWORD": "your-password",
        "SSH_PORT": "22"
      }
    }
  }
}
```

> **注意**: 如果 PATH 配置有问题，也可以使用完整的 npm 路径，避免解析歧义：
> ```json
> { "command": "npx", "args": ["ssh-licco"] }
> ```

### pip 版本配置（conda 环境中）

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "/path/to/conda/env/Scripts/ssh-licco.exe",
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

---

## 🔍 环境诊断

安装时自动显示诊断信息，帮助你了解当前环境状况：

```
============================================================
🚀 ssh-licco Installer
============================================================
🔍 Diagnosing Python environment...
  ✅ D:\Users\Name\AppData\Local\Programs\Python\Python312\python.exe: Python 3.12.0
  ⚠️  python: Python 3.11.5 (Anaconda - used as last resort)

📦 Package path: C:\path\to\ssh-licco
🌐 Virtual environment: C:\Users\Name\.ssh-licco-venv

🔧 Creating isolated virtual environment...
   Using D:\software\anaconda\python.exe (no standalone Python found)
   ✅ Virtual environment created successfully
```

诊断信息的解读：

| 信息 | 含义 |
|------|------|
| `✅ python: Python 3.12.0` | 找到了独立安装的 Python，优先使用 |
| `⚠️ python: Python 3.11.5 (Anaconda)` | 只有 Anaconda 可用，作为最后手段 |
| `⚠️ Multiple installations found` | 多个 ssh-licco 入口，检查 PATH 配置 |
| `⚠️ ssh-licco resolves to Anaconda` | ssh-licco 命令被 Anaconda 抢占了，需调整 PATH |

---

## ❓ 常见问题

### Q: 安装时会修改我的 conda 环境吗？

**A:** 不会！npm 版本使用独立的虚拟环境（`~/.ssh-licco-venv`），pip 版本只在当前激活的 conda 环境中安装，不会影响其他环境。

### Q: 我的 ssh-licco 命令来自 Anaconda，不是 npm，怎么办？

**A:** 这是 PATH 顺序问题，请按以下步骤修复：
1. 在系统环境变量中将 `node_global` 目录移到 Anaconda 之前
2. 清理 Anaconda 中的残留入口：`pip uninstall ssh-licco`
3. 重启终端后检查：`where ssh-licco`

### Q: npm postinstall 卡住了或者创建 venv 失败怎么办？

**A:** 手动执行 postinstall：
```bash
npm install -g ssh-licco --ignore-scripts
node D:\software\nodejs\node_global\node_modules\ssh-licco\install.js
```

### Q: 如何完全卸载并重装？

```bash
# 卸载 npm 版本
npm uninstall -g ssh-licco

# 删除独立 venv
Remove-Item -Recurse -Force ~/.ssh-licco-venv

# 清理 Anaconda 中的残留
pip uninstall ssh-licco -y

# 重装
npm install -g ssh-licco
```

### Q: 可以在 base conda 环境中安装 pip 版本吗？

**A:** 可以，但推荐 npm 版本（完全隔离），或者创建专用 conda 环境安装。

---

## 📝 最佳实践

1. **首选 npm 安装** — 与 Anaconda 完全隔离，无需管理 Python 环境
2. **调整 PATH 顺序** — 确保 `node_global` 在 Anaconda 之前
3. **清理残留入口** — 安装后检查 `where ssh-licco`，删除多余的入口
4. **使用独立 venv** — 不要手动修改 `~/.ssh-licco-venv` 中的内容
5. **环境变量管理** — 敏感信息使用环境变量，不要硬编码在配置文件中

---

## 📚 相关文档

- [快速开始指南](./QUICKSTART.md)
- [使用说明](./USAGE.md)
- [完整 README](./README.md)
- [故障排除指南](./docs/skills/ssh-mcp-troubleshoot/SKILL.md)