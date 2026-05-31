# 🚀 ssh-licco 发布技能

## 📋 技能概述

这个技能帮助你完成 ssh-licco 项目的完整发布流程。这是一个**高度自动化**的流水线，一次 tag push 即可触发全链路。

---

## 🎯 适用场景

当你需要：
- ✅ 修复 bug 后发布新版本
- ✅ 添加新功能后发布
- ✅ 定期维护更新
- ✅ 紧急安全补丁

---

## 📝 完整发布流程

### 概览：一次 push 全自动

```
git tag -a vX.Y.Z -m "message"
git push github vX.Y.Z
                         ↓
                  auto-release.yml 检测到 tag push
                         ↓
              自动创建 GitHub Release
                         ↓
              release:published 事件触发
                  ↙              ↘
            pypi.yml      mcp-registry.yml
            (发布 PyPI)    (注册 MCP Registry)
```

---

### 阶段 1：代码准备

#### 1.1 确保代码已推送

```bash
git status                    # 确保无未提交改动
git push github master         # 推送到 GitHub
```

#### 1.2 更新版本号

编辑以下文件：

**`pyproject.toml`**：
```toml
[project]
version = "1.1.0"  # 递增为新版本
```

**`ssh_mcp/__init__.py`**：
```python
__version__ = "1.1.0"  # 同步更新
```

#### 1.3 更新文档

- **README.md**: 版本历史表格新增一行
- **USAGE.md**: 如有工具变动则更新

#### 1.4 提交版本更新

```bash
git add -A
git commit -m "chore: release v1.1.0

Features:
- MCP 工具从 15 个精简为 7 个
- 自动连接、智能后台检测

Docs:
- 更新 README 和 USAGE"
git push github master
```

---

### 阶段 2：本地测试（⚠️ 必须）

#### 2.1 重新安装

```bash
pip install -e . --force-reinstall --no-deps
```

#### 2.2 验证版本

```bash
ssh-licco --version
# 输出: ssh-licco 1.1.0
```

#### 2.3 MCP 工具验证

确认工具数量和名称正确：

```python
from ssh_mcp.server import SSHMCPServer
import asyncio

s = SSHMCPServer()
tools = asyncio.run(s.server._tool_manager.list_tools())
print([t.name for t in tools])
print(f"Total: {len(tools)}")
```

#### 2.4 功能冒烟测试

```bash
# CLI 连通性测试
ssh-licco --version
ssh-licco list-hosts
ssh-licco exec "echo OK"   # 需要配置环境变量
```

---

### 阶段 3：发布（⚠️ 使用 `--tags` 而非 `--tags`）

> **关键规则**：只 push tag，不要 push `--tags`（会推送所有历史 tag）。

#### 3.1 创建并推送 tag

```bash
git tag -a v1.1.0 -m "v1.1.0: MCP 工具精简为 7 个"
git push github v1.1.0
```

#### 3.2 自动触发的内容

推完 tag 后，GitHub Actions 自动完成：

| 步骤 | Workflow | 说明 |
|------|----------|------|
| ① 创建 Release | `auto-release.yml` | `gh release create` 自动生成 Release Notes |
| ② 发布 PyPI | `pypi.yml` | `python -m build` + PyPI publish |
| ③ 注册 MCP | `mcp-registry.yml` | 更新 MCP Registry |

> ⚠️ **注意**：如果 tag 已存在但 Release 没创建（如之前手动打 tag 漏建了 Release），
> 可以直接去 GitHub Releases 页面手动创建，不需要重新打 tag。

---

### 阶段 4：验证发布

#### 4.1 检查 Actions 运行

访问：https://github.com/Echoqili/ssh-licco/actions

确认三个 workflow 全部绿 ✅

#### 4.2 检查 PyPI

访问：https://pypi.org/project/ssh-licco/

确认新版本已上线

#### 4.3 检查 GitHub Release

访问：https://github.com/Echoqili/ssh-licco/releases

确认 Release Notes 正确生成

#### 4.4 检查 MCP Registry

访问：https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

---

## 📋 发布检查清单

### 发布前

- [ ] 代码已提交并推送
- [ ] 本地测试通过
- [ ] 版本号已更新（pyproject.toml + __init__.py）
- [ ] README 版本历史已更新
- [ ] 文档已同步更新

### 发布中

- [ ] `git tag -a vX.Y.Z -m "..."` 已创建
- [ ] `git push github vX.Y.Z` 已推送
- [ ] 确认 Actions 已触发

### 发布后

- [ ] auto-release ✅（Release 创建成功）
- [ ] pypi.yml ✅（PyPI 发布成功）
- [ ] mcp-registry.yml ✅（MCP Registry 更新成功）
- [ ] 全新安装测试通过

---

## 🎯 自动化流水线详解

### auto-release.yml（新增于 v1.1.0）

```yaml
name: Auto Release on Tag

on:
  push:
    tags:
      - 'v*'              # v 开头 tag 的 push 触发

jobs:
  create-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write      # 必须有 write 权限才能创建 Release
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG_NAME=${GITHUB_REF#refs/tags/}
          gh release create "$TAG_NAME" --title "$TAG_NAME" --generate-notes
```

### pypi.yml

```yaml
on:
  release:
    types: [published]     # Release 创建后触发
  workflow_dispatch:        # 也支持手动触发
```

### mcp-registry.yml

```yaml
on:
  release:
    types: [published]
  workflow_dispatch:
```

---

## 💡 经验总结

### DO（推荐做法）

| 做法 | 说明 |
|------|------|
| `git push github vX.Y.Z` | **只 push 指定 tag**，不会意外推送历史 tag |
| 先 push master 再 push tag | 确保 tag 指向最新 commit |
| tag 前做本地冒烟测试 | `ssh-licco --version` + `list-hosts` |
| 版本号双更新 | pyproject.toml + __init__.py 同步改 |

### DON'T（避免做法）

| 做法 | 问题 |
|------|------|
| `git push github --tags` | 会把所有历史 tag 全推上去，包括旧的/废弃的 |
| 只打 tag 不 push | tag 只在本地的，GitHub Actions 触发不了 |
| 手动去网页建 Release | 现在有 `auto-release.yml`，不需要了 |
| `requires-python = ">=3.10,<3.14"` | 上限 `<3.14` 会阻止未来 Python 版本安装，用 `>=3.10` |

---

### 为什么 `git push github --tags` 危险

```bash
# 危险 - 会把所有本地 tag 推上去
git push github --tags

# 安全 - 只推送指定的那一个
git push github v1.1.0
```

如果你本地有旧的、没清理的 tag（如 `test-tag`、`v0.1-dev`），`--tags` 会全部推上去，可能触发意外的 Release。

---

## 📊 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.1.0 | 2026-06-01 | 🔥 精简重构：15 → 7 工具，自动连接，智能后台检测 |
| v1.0.0 | 2026-05-31 | 🎉 首个主要版本，CLI 增强，402 测试用例 |

---

## 🔗 相关资源

- [PyPI 文档](https://packaging.python.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [MCP Registry](https://modelcontextprotocol.io/)
- [Semantic Versioning](https://semver.org/)

---

**祝你发布顺利！** 🎉