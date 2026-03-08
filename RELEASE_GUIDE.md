# 📦 ssh-licco 发布到 PyPI 和 MCP Registry 完整指南

## 📋 目录

1. [发布流程总结](#发布流程总结)
2. [关键问题和解决方案](#关键问题和解决方案)
3. [自动化脚本](#自动化脚本)
4. [最佳实践](#最佳实践)
5. [常见问题](#常见问题)

---

## 🎯 发布流程总结

### 完整步骤

1. **准备阶段**
   - ✅ 确保代码已完成并测试通过
   - ✅ 更新 `pyproject.toml` 中的版本号
   - ✅ 在 README.md 中添加 `<!-- mcp-name: io.github.Echoqili/ssh-licco -->`

2. **发布到 PyPI**
   - ✅ 创建 GitHub Release（会自动触发 GitHub Actions）
   - ✅ 配置 `PYPI_API_TOKEN` secret
   - ✅ 等待 GitHub Actions 完成构建和发布

3. **发布到 MCP Registry**
   - ✅ 确保 PyPI 包已可用
   - ✅ 确保 README 包含 mcp-name 标识
   - ✅ 使用 Registry API 发布服务器元数据

---

## 🔧 关键问题和解决方案

### 问题 1：GitHub Release 标签冲突

**问题描述：**
```
Duplicate tag name - tag name has already been taken
```

**解决方案：**
```python
# 1. 删除现有 release
requests.delete(f"{BASE_URL}/releases/{release_id}")

# 2. 删除标签
requests.delete(f"{BASE_URL}/git/refs/tags/{TAG}")

# 3. 创建新的 release
requests.post(f"{BASE_URL}/releases", json=release_data)
```

**经验教训：**
- 发布前先检查标签是否已存在
- 使用版本号管理工具避免冲突

---

### 问题 2：PyPI 发布失败 - 版本已存在

**问题描述：**
```
HTTPError: 400 Bad Request
File already exists ('ssh_licco-0.2.1-py3-none-any.whl')
```

**解决方案：**
1. **方案 A**：删除 PyPI 上的现有版本
   - 访问：https://pypi.org/manage/project/ssh-licco/releases/
   - 找到对应版本，点击 "Delete version"

2. **方案 B**：升级版本号（推荐）
   - 修改 `pyproject.toml`: `version = "0.1.2"`
   - 创建新的 GitHub Release

**经验教训：**
- 每次发布前递增版本号
- 使用语义化版本控制（Semantic Versioning）

---

### 问题 3：GitHub Actions PyPI 发布失败

**问题描述：**
```
Publish to PyPI - failure
```

**原因：** 缺少 Trusted Publisher 配置或 Token 配置错误

**解决方案 1：使用 Trusted Publisher（推荐）**
```yaml
jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
    - uses: actions/checkout@v4
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      # 不需要 password，Trusted Publisher 会自动处理
```

配置步骤：
1. 访问：https://pypi.org/manage/project/ssh-licco/settings/publishing/
2. 添加 publisher: GitHub Actions
3. 填写仓库信息

**解决方案 2：使用 PYPI_API_TOKEN**
```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    user: __token__
    password: ${{ secrets.PYPI_API_TOKEN }}
```

配置步骤：
1. 在 PyPI 生成 API Token
2. 在 GitHub 添加 secret: `PYPI_API_TOKEN`

**经验教训：**
- Trusted Publisher 更安全，推荐用于生产环境
- Token 方式更简单，适合快速测试

---

### 问题 4：MCP Registry 发布失败 - 所有权验证

**问题描述：**
```
400 Bad Request
PyPI package 'ssh-licco' ownership validation failed.
The server name 'io.github.Echoqili/ssh-licco' must appear as 
'mcp-name: io.github.Echoqili/ssh-licco' in the package README
```

**解决方案：**
在 README.md 顶部添加：
```markdown
# 🚀 SSH LICCO

<!-- mcp-name: io.github.Echoqili/ssh-licco -->

[![PyPI version](...)](...)
```

**重要：**
- 必须发布到 PyPI 后，MCP Registry 才能读取到最新的 README
- 需要创建新的 release 来触发 PyPI 发布

**经验教训：**
- MCP Registry 通过 PyPI 包验证所有权
- README 的变更需要重新发布到 PyPI 才生效

---

### 问题 5：网络连接问题

**问题描述：**
```
fatal: unable to access 'https://github.com/...':
Failed to connect to github.com port 443
```

**解决方案：**

**方案 1：使用 Git 命令重试**
```bash
git push github master
```

**方案 2：使用 GitHub API 推送**
```python
# 通过 API 更新文件
requests.put(
    f"{BASE_URL}/contents/{file}",
    json={
        "message": "commit message",
        "content": base64_content,
        "sha": current_sha,
        "branch": "master"
    }
)
```

**方案 3：使用 GitHub CLI**
```bash
gh repo push
```

**经验教训：**
- 准备多种推送方式
- API 方式可以作为 git push 的备选

---

##  自动化脚本

### 1. 推送代码并创建 Release

```python
# push_and_release.py
import requests
import base64

# 更新 pyproject.toml
# 创建 commit
# 创建 GitHub Release
```

### 2. 监控工作流并发布到 MCP Registry

```python
# auto_publish_mcp.py
import requests
import time

# 监控 GitHub Actions
# 等待 PyPI 发布完成
# 发布到 MCP Registry
```

### 3. 一键发布脚本

```bash
# 更新版本号
# 推送到 GitHub
# 创建 Release
# 等待 PyPI 发布
# 发布到 MCP Registry
```

---

## ✨ 最佳实践

### 1. 版本管理

- ✅ 使用语义化版本（Semantic Versioning）
- ✅ 每次发布前递增版本号
- ✅ 在 CHANGELOG.md 中记录变更

### 2. CI/CD 配置

- ✅ 使用 GitHub Actions 自动发布
- ✅ 配置适当的权限（id-token: write）
- ✅ 使用 secrets 管理敏感信息

### 3. 文档维护

- ✅ README 包含 mcp-name 标识
- ✅ 保持文档与代码同步
- ✅ 提供清晰的安装和使用说明

### 4. 错误处理

- ✅ 检查标签是否已存在
- ✅ 检查 PyPI 版本是否已发布
- ✅ 准备回滚方案

---

## ❓ 常见问题

### Q1: 如何删除 PyPI 上的包？

**A:** 
1. 访问 https://pypi.org/manage/project/YOUR_PROJECT/
2. 找到要删除的版本
3. 点击 "Delete version"

注意：PyPI 不允许删除整个项目，只能删除特定版本。

### Q2: GitHub Actions 一直失败怎么办？

**A:**
1. 检查 workflow 文件配置
2. 验证 secrets 是否正确
3. 查看详细日志定位问题
4. 尝试手动触发工作流

### Q3: MCP Registry 发布后看不到？

**A:**
1. 检查 PyPI 包是否可用
2. 验证 README 包含 mcp-name
3. 等待 MCP Registry 同步（可能需要几分钟）
4. 访问：https://registry.modelcontextprotocol.io/servers/YOUR_SERVER

### Q4: 如何测试发布流程？

**A:**
1. 使用 TestPyPI 测试 PyPI 发布
2. 使用 draft release 测试 GitHub Actions
3. 在开发环境测试 MCP Registry API

---

## 📊 完整发布命令参考

### 本地测试
```bash
# 构建包
python -m build

# 测试上传到 TestPyPI
twine upload --repository testpypi dist/*

# 上传到正式 PyPI
twine upload dist/*
```

### GitHub Release
```bash
# 提交代码
git add .
git commit -m "chore: bump version to 0.1.2"
git push

# 创建标签
git tag v0.1.2
git push origin v0.1.2
```

### MCP Registry API
```python
# 获取 token
POST https://registry.modelcontextprotocol.io/v0.1/auth/github-at
{
  "github_token": "ghp_..."
}

# 发布服务器
POST https://registry.modelcontextprotocol.io/v0.1/publish
{
  "name": "io.github.Echoqili/ssh-licco",
  "version": "0.1.2",
  ...
}
```

---

## 🔗 相关资源

- [PyPI 官方文档](https://pypi.org/help/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [MCP Registry 文档](https://modelcontextprotocol.io/docs)
- [语义化版本规范](https://semver.org/)
- [Trusted Publisher 指南](https://docs.pypi.org/trusted-publishers/)

---

## 📝 总结

发布 ssh-licco 到 PyPI 和 MCP Registry 的完整流程已经自动化。关键要点：

1. **版本号管理** - 每次发布前递增版本
2. **README 标识** - 添加 mcp-name 用于 MCP Registry 验证
3. **GitHub Actions** - 自动构建和发布到 PyPI
4. **Registry API** - 发布到 MCP Registry

通过遵循本指南，可以确保发布流程顺利进行。

---

*Last updated: 2026-03-08*
*Version: 0.1.2*
