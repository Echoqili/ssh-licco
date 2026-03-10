# 版本管理与发布指南

## 📌 版本号规范

本项目遵循 [语义化版本 (SemVer)](https://semver.org/lang/zh-CN/)：

```
主版本号.次版本号.修订号
   MAJOR   .  MINOR  .  PATCH
```

| 版本类型 | 规则 | 示例 |
|----------|------|------|
| **MAJOR** | 不兼容的 API 变更 | 1.0.0 → 2.0.0 |
| **MINOR** | 向后兼容的新功能 | 1.0.0 → 1.1.0 |
| **PATCH** | 向后兼容的问题修复 | 1.0.0 → 1.0.1 |

---

## 🔄 版本同步

### 同步文件

版本信息存储在以下位置，**修改一处即可自动同步**：

| 文件 | 说明 |
|------|------|
| `ssh_mcp/__init__.py` | **主版本文件**（修改这个） |
| `pyproject.toml` | 自动同步 |
| `VERSION` | 备份文件 |

### 方式 1：使用同步脚本（推荐）

```bash
# 更新到新版本
python sync_version.py 0.1.7

# 查看当前版本
python -c "from ssh_mcp import __version__; print(__version__)"
```

### 方式 2：手动修改

```bash
# 1. 修改主版本文件
# 文件: ssh_mcp/__init__.py
# 修改第 5 行: __version__ = "0.1.7"

# 2. 同步到 pyproject.toml
# 文件: pyproject.toml
# 修改第 3 行: version = "0.1.7"
```

---

## 🐛 Bug 修复版本规则

### PATCH (修订号) - 小修复

**需要升 PATCH 的情况**：
- ✅ Bug 修复
- ✅ 性能优化
- ✅ 文档修正
- ✅ 小的功能改进

**示例**：
```bash
# 修复密码显示问题
python sync_version.py 1.0.1
```

### MINOR (次版本号) - 新功能

**需要升 MINOR 的情况**：
- ✅ 新增工具（ssh_list_hosts, ssh_add_host 等）
- ✅ 新增功能
- ✅ 向后兼容的 API 扩展
- ✅ 废弃功能的标记

**示例**：
```bash
# 添加服务器管理功能
python sync_version.py 1.1.0
```

### MAJOR (主版本号) - 重大变更

**需要升 MAJOR 的情况**：
- ❌ 不兼容的 API 变更
- ❌ 移除现有功能
- ❌ 重大架构调整

**示例**：
```bash
# 重大版本更新
python sync_version.py 2.0.0
```

---

## 📋 Bug 修复清单

根据修改内容，选择对应的版本升级：

| 修改类型 | 版本类型 | 示例命令 |
|----------|----------|----------|
| 修复密码显示问题 | PATCH | `python sync_version.py 1.0.1` |
| 添加新工具（ssh_list_hosts） | MINOR | `python sync_version.py 1.1.0` |
| 修复连接超时问题 | PATCH | `python sync_version.py 1.0.2` |
| 添加 SSH 密钥认证 | MINOR | `python sync_version.py 1.2.0` |
| 移除废弃 API | MAJOR | `python sync_version.py 2.0.0` |
| 修复安全漏洞 | PATCH | `python sync_version.py 1.0.3` |
| 优化性能 | PATCH | `python sync_version.py 1.0.4` |
| 添加 Docker 管理功能 | MINOR | `python sync_version.py 1.3.0` |

---

## 🚀 发布流程

### 1. 本地测试

```bash
# 安装最新版本
pip install -e . --user

# 测试功能
python -c "from ssh_mcp import __version__; print(__version__)"
```

### 2. 更新版本

```bash
# 根据修改类型选择版本
python sync_version.py 1.0.1  # Bug 修复
# 或
python sync_version.py 1.1.0  # 新功能
```

### 3. 构建包

```bash
# 清理旧构建
rm -rf dist/ build/ *.egg-info/

# 构建新包
python -m build
```

### 4. 发布到 PyPI

```bash
# 使用 Twine 上传
python -m twine upload dist/* -u __token__ -p <YOUR_PYPI_TOKEN>
```

### 5. 创建 GitHub Release

```bash
# 推送代码
git add .
git commit -m "chore: bump version to 1.0.1"
git push origin master

# 创建 Release
git tag v1.0.1
git push origin v1.0.1
```

---

## 📝 版本更新日志

每次版本更新请记录：

```markdown
## [1.0.1] - 2026-03-11

### 修复
- 修复密码在 MCP 响应中显示的问题
- 修复版本号不统一的问题

### 文档
- 添加版本管理指南
```

---

## ✅ 快速参考

```bash
# 查看当前版本
python -c "from ssh_mcp import __version__; print(__version__)"

# 更新版本（Bug 修复）
python sync_version.py 1.0.1

# 更新版本（新功能）
python sync_version.py 1.1.0

# 更新版本（重大变更）
python sync_version.py 2.0.0

# 构建发布
python -m build

# 上传到 PyPI
python -m twine upload dist/*
```

---

**文档更新时间**: 2026-03-11
**当前版本**: 1.0.1
