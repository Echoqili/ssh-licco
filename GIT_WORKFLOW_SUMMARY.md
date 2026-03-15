# 🌿 Git 分支管理技能 - 使用指南

## ✅ 已创建文档

**文件位置**:
- **Git 版本控制**: [`docs/skills/GIT_WORKFLOW_SKILL.md`](file:///d:/pyworkplace/ssh-mcp/docs/skills/GIT_WORKFLOW_SKILL.md)
- **Trae IDE 本地**: [`.trae/skills/GIT_WORKFLOW_SKILL.md`](file:///d:/pyworkplace/ssh-mcp/.trae/skills/GIT_WORKFLOW_SKILL.md)

**提交状态**: ✅ 已推送到 GitHub  
**Commit**: `294af34`

---

## 🎯 完整开发流程（7 步）

### 阶段 1：开始新功能

```bash
# 1. 切换到 master 分支
git checkout master

# 2. 拉取最新代码
git pull github master

# 3. 创建特性分支
git checkout -b feat/feature-name
```

### 阶段 2：开发功能

```bash
# 编写代码
# ...

# 提交代码
git add <files>
git commit -m "feat: add new feature

Detailed description"
```

### 阶段 3：完成功能开发

```bash
# 1. 切换回 master
git checkout master

# 2. 拉取最新代码
git pull github master

# 3. 推送特性分支
git push -u github feat/feature-name
```

### 阶段 4：创建 Pull Request

**使用 GitHub CLI**:
```bash
gh pr create \
  --base master \
  --head feat/feature-name \
  --title "feat: Add new feature" \
  --body "## Description..."
```

**或手动创建**:
1. 访问 GitHub 仓库
2. Pull requests → New pull request
3. base: `master`, compare: `feat/feature-name`
4. 填写标题和描述
5. Create pull request

### 阶段 5：Code Review

```bash
# 在特性分支上修改
git checkout feat/feature-name

# 修改代码
# ...

# 提交修改
git add <files>
git commit -m "fix: address review comments"

# 推送
git push github feat/feature-name
```

### 阶段 6：合并 PR

管理员在 GitHub 上合并 PR（推荐 Squash and Merge）

### 阶段 7：清理本地分支

```bash
# 1. 切换回 master
git checkout master

# 2. 拉取最新代码
git pull github master

# 3. 删除本地分支
git branch -d feat/feature-name
```

---

## 📝 实际示例

### 开发安全增强功能

```bash
# 阶段 1：开始
git checkout master
git pull github master
git checkout -b feat/security-enhancements

# 阶段 2：开发
# 编写代码...
git add ssh_mcp/security.py
git commit -m "feat: add multi-level security configuration"

# 阶段 3：完成
git checkout master
git pull github master
git push -u github feat/security-enhancements

# 阶段 4：创建 PR
gh pr create \
  --base master \
  --head feat/security-enhancements \
  --title "feat: Add flexible security configuration"

# 阶段 5-6：Review 和合并（在 GitHub 上）

# 阶段 7：清理
git checkout master
git pull github master
git branch -d feat/security-enhancements
```

---

## 🔧 Git 别名配置

添加到 `~/.gitconfig`:

```ini
[alias]
    # 快速拉取和推送
    plgm = pull github master
    psgm = push github master
    
    # 常用命令
    br = branch
    co = checkout
    st = status
    ci = commit
    
    # 查看日志
    lg = log --oneline --graph --decorate
```

使用：
```bash
git plgm  # git pull github master
git lg    # git log --oneline --graph --decorate
```

---

## 📋 分支命名规范

| 类型 | 命名 | 示例 |
|------|------|------|
| 新功能 | `feat/xxx` | `feat/add-security` |
| Bug 修复 | `fix/xxx` | `fix/resolve-memory-leak` |
| 文档更新 | `docs/xxx` | `docs/add-readme` |
| 重构 | `refactor/xxx` | `refactor/improve-performance` |
| 测试 | `test/xxx` | `test/add-unit-tests` |

---

## ✨ 提交信息规范

### 格式

```
<type>: <subject>

<body>
```

### Type 类型

- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `style:` - 代码格式
- `refactor:` - 重构
- `test:` - 测试
- `chore:` - 构建/工具

### 示例

```bash
# 好
feat: add user authentication

Detailed description of the authentication system.
- Add login endpoint
- Add JWT token generation
- Add session management

# 不好
update code
```

---

## 🔗 相关文档

- **[docs/skills/RELEASE_SKILL.md](docs/skills/RELEASE_SKILL.md)** - 发布流程指南
- **[docs/skills/ssh-mcp-dev/SKILL.md](docs/skills/ssh-mcp-dev/SKILL.md)** - 开发指南
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - 完整文档索引

---

## 💡 最佳实践

### ✅ 推荐

- 每个功能一个分支
- 频繁提交小改动
- 保持分支与 master 同步
- PR 描述详细清晰
- 及时 Code Review

### ❌ 避免

- 在 master 分支直接开发
- 长时间不合并的分支
- 巨大的提交（>500 行）
- 模糊的提交信息
- 跳过 Code Review

---

## 🎯 工作流程可视化

```
master:     o---o---o---o---o---o---o
             \         \         /
feat/A:       o---o---o         |
               \                 \
feat/B:         o---o---o---o---o
```

---

**Git 分支管理技能已创建完成！现在可以开始规范开发了！** 🚀

*Created: 2026-03-14*  
*Status: ✅ Complete*  
*Location: docs/skills/GIT_WORKFLOW_SKILL.md*
