# 🌿 Git 分支管理技能

## 📋 技能概述

这个技能指导你使用规范的 Git 分支管理流程进行开发，确保代码质量和版本控制的规范性。

---

## 🎯 分支策略

### 分支类型

| 分支类型 | 命名规范 | 用途 | 生命周期 |
|---------|---------|------|---------|
| **主分支** | `master` / `main` | 生产环境代码 | 永久 |
| **特性分支** | `feat/xxx` | 新功能开发 | 功能完成后合并 |
| **修复分支** | `fix/xxx` | Bug 修复 | 修复后合并 |
| **文档分支** | `docs/xxx` | 文档更新 | 完成后合并 |

### 分支保护

- ✅ `master` 分支受保护
- ✅ 所有改动必须通过 PR 合并
- ✅ PR 需要 Code Review
- ✅ 通过 CI/CD 检查

---

## 🚀 完整开发流程

### 阶段 1：开始新功能

#### 1.1 切换到 master 分支

```bash
git checkout master
```

#### 1.2 拉取最新代码

```bash
git pull github master
```

**注意**: 使用 `github` 远程仓库，不是 `origin`

#### 1.3 创建特性分支

```bash
git checkout -b feat/feature-name
```

**命名规范**:
- `feat/add-new-feature` - 新功能
- `feat/security-enhancements` - 安全增强
- `feat/performance-improvement` - 性能优化

---

### 阶段 2：开发功能

#### 2.1 编写代码

在特性分支上进行开发。

#### 2.2 提交代码

```bash
git add <files>
git commit -m "feat: add new feature

Detailed description of the feature.
- Feature 1
- Feature 2
- Feature 3"
```

**提交信息规范**:
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `style:` - 代码格式
- `refactor:` - 重构
- `test:` - 测试
- `chore:` - 构建/工具

#### 2.3 保持与 master 同步（可选）

如果开发周期较长：

```bash
git fetch github master
git rebase github/master
```

---

### 阶段 3：完成功能开发

#### 3.1 切换回 master 分支

```bash
git checkout master
```

#### 3.2 拉取最新代码

```bash
git pull github master
```

#### 3.3 推送到远程特性分支

```bash
git push -u github feat/feature-name
```

---

### 阶段 4：创建 Pull Request

#### 4.1 使用 GitHub CLI 创建 PR

```bash
gh pr create \
  --base master \
  --head feat/feature-name \
  --title "feat: Add new feature" \
  --body "## 🎯 Description

Description of the feature.

## ✅ Checklist

- [ ] Code reviewed
- [ ] Tests added
- [ ] Documentation updated

## 🔗 Related Issues

Closes #123"
```

#### 4.2 或手动创建 PR

1. 访问 GitHub 仓库
2. 点击 "Pull requests"
3. 点击 "New pull request"
4. 选择:
   - base: `master`
   - compare: `feat/feature-name`
5. 填写 PR 标题和描述
6. 点击 "Create pull request"

---

### 阶段 5：Code Review

#### 5.1 等待 Review

- 通知团队成员 Review
- 回复 Review 意见
- 根据意见修改代码

#### 5.2 修改代码

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

---

### 阶段 6：合并 PR

#### 6.1 合并 PR（管理员）

**方式 1: Squash and Merge** (推荐)
- 将所有提交压缩为一个
- 保持 master 历史清晰

**方式 2: Merge**
- 保留所有提交历史
- 适合重要的功能分支

**方式 3: Rebase and Merge**
- 线性历史
- 不保留合并提交

#### 6.2 删除特性分支

合并后删除远程分支：

```bash
git push github --delete feat/feature-name
```

---

### 阶段 7：清理本地分支

#### 7.1 切换回 master

```bash
git checkout master
```

#### 7.2 拉取最新代码

```bash
git pull github master
```

#### 7.3 删除本地特性分支

```bash
git branch -d feat/feature-name
```

如果分支未完全合并：

```bash
git branch -D feat/feature-name
```

---

## 📝 完整流程示例

### 示例：开发安全增强功能

#### 1. 开始功能

```bash
# 切换到 master
git checkout master

# 拉取最新代码
git pull github master

# 创建特性分支
git checkout -b feat/security-enhancements
```

#### 2. 开发功能

```bash
# 编写代码
# ...

# 提交代码
git add ssh_mcp/security.py
git commit -m "feat: add multi-level security configuration

- Add SecurityLevel enum (STRICT, BALANCED, RELAXED)
- Add environment variable configuration
- Add user-friendly error messages
- Add comprehensive documentation"
```

#### 3. 完成开发

```bash
# 切换回 master
git checkout master

# 拉取最新代码
git pull github master

# 推送特性分支
git push -u github feat/security-enhancements
```

#### 4. 创建 PR

```bash
gh pr create \
  --base master \
  --head feat/security-enhancements \
  --title "feat: Add flexible security configuration" \
  --body "## 🎯 New Features

- Multi-level security strategy (STRICT/BALANCED/RELAXED)
- Environment variable configuration
- User-friendly error messages

## ✅ Testing

- [x] All tests passed
- [x] Documentation updated
- [x] Security review completed"
```

#### 5. 等待 Review 和合并

#### 6. 合并后清理

```bash
# 切换回 master
git checkout master

# 拉取最新代码
git pull github master

# 删除本地分支
git branch -d feat/security-enhancements
```

---

## 🛠️ Git 别名配置

### 推荐别名

添加到 `~/.gitconfig`:

```ini
[alias]
    # 分支管理
    br = branch
    co = checkout
    st = status
    ci = commit
    df = diff
    
    # 拉取和推送
    pl = pull
    ps = push
    plgm = pull github master
    psgm = push github master
    
    # 日志
    lg = log --oneline --graph --decorate
    last = log -1 HEAD
    
    # 清理
    cleanup = !git branch -merged | grep -v '\\*' | xargs -n 1 git branch -d
```

### 使用别名

```bash
git plgm  # git pull github master
git psgm  # git push github master
git lg    # 查看提交历史
```

---

##  Git 工作流可视化

```
master:     o---o---o---o---o---o---o
             \         \         /
feat/A:       o---o---o         |
               \                 \
feat/B:         o---o---o---o---o
```

---

## ⚠️ 常见问题

### Q1: 如何查看远程分支？

```bash
git branch -r
```

### Q2: 如何删除已合并的分支？

```bash
# 本地
git branch --merged | grep -v '\*' | xargs git branch -d

# 远程
git push github --delete feat/old-feature
```

### Q3: 如何解决合并冲突？

```bash
# 1. 拉取最新代码
git checkout master
git pull github master

# 2. 切换到特性分支
git checkout feat/feature-name

# 3. 合并 master
git merge master

# 4. 解决冲突
# 编辑冲突文件

# 5. 提交解决
git add <files>
git commit -m "fix: resolve merge conflicts"

# 6. 推送
git push github feat/feature-name
```

### Q4: 如何撤销提交？

**撤销未推送的提交**:

```bash
git reset --soft HEAD~1  # 保留更改
git reset --hard HEAD~1  # 丢弃更改
```

**撤销已推送的提交**:

```bash
git revert <commit-hash>
git push github master
```

---

## 🎯 最佳实践

### 1. 分支命名

- ✅ `feat/add-login` - 清晰描述功能
- ✅ `fix/resolve-bug-123` - 关联 Issue
- ❌ `test` - 太模糊
- ❌ `my-feature` - 不清晰

### 2. 提交信息

- ✅ `feat: add user authentication`
- ✅ `fix: resolve memory leak in parser`
- ❌ `update` - 太模糊
- ❌ `fix bug` - 不具体

### 3. PR 描述

- ✅ 详细描述功能
- ✅ 添加测试截图
- ✅ 关联相关 Issue
- ❌ 只有标题
- ❌ 没有说明

### 4. Code Review

- ✅ 及时 Review 他人代码
- ✅ 提供建设性意见
- ✅ 保持礼貌和尊重
- ❌ 拖延 Review
- ❌ 人身攻击

---

## 📚 相关资源

- [Git 官方文档](https://git-scm.com/doc)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Branching Model](https://nvie.com/posts/a-successful-git-branching-model/)

---

## 🔗 相关 Skills

- **[ssh-mcp-dev/SKILL.md](ssh-mcp-dev/SKILL.md)** - 开发指南
- **[RELEASE_SKILL.md](RELEASE_SKILL.md)** - 发布流程
- **[ssh-mcp-ops/SKILL.md](ssh-mcp-ops/SKILL.md)** - 运维操作

---

**遵循规范的 Git 分支管理流程，让团队协作更高效！** 🚀

*Last updated: 2026-03-14*  
*Version: 1.0*
