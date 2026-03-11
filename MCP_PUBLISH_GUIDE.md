# 📦 MCP Registry 发布指南

## ✅ 当前状态

你的 `ssh-licco` 已经成功发布到 MCP Registry：
- **服务器名称**: `io.github.Echoqili/ssh-licco`
- **当前最新版本**: 0.1.3 (Registry) vs 0.1.7 (PyPI)
- **状态**: Active
- **查看地址**: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

## 🎯 发布最新版本 (0.1.7)

### 方式一：使用 GitHub Actions 自动发布（推荐）

我已经为你创建了自动发布工作流，只需要设置 GitHub Token：

#### 1. 创建 GitHub Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 填写说明（如 "MCP Registry Publish"）
4. 勾选权限：
   - ✅ `repo` (Full control of private repositories)
5. 点击 "Generate token"
6. **复制 token**（只显示一次！）

#### 2. 添加 GitHub Secret

1. 访问：https://github.com/Echoqili/ssh-licco/settings/secrets/actions
2. 点击 "New repository secret"
3. 添加：
   - **Name**: `GITHUB_TOKEN`
   - **Value**: 粘贴刚才复制的 token
4. 点击 "Add secret"

#### 3. 触发发布

**方法 A**: 创建新的 GitHub Release
```bash
git tag v0.1.7
git push origin v0.1.7
```

**方法 B**: 手动触发 Workflow
1. 访问：https://github.com/Echoqili/ssh-licco/actions/workflows/mcp-registry.yml
2. 点击 "Run workflow"
3. 选择分支（main/master）
4. 点击 "Run workflow"

---

### 方式二：本地手动发布

如果你想在本地直接发布：

#### 1. 设置环境变量

```powershell
# Windows PowerShell
$env:GITHUB_TOKEN="your_github_token_here"

# 或永久设置
setx GITHUB_TOKEN "your_github_token_here"
```

#### 2. 运行发布脚本

```bash
python publish_mcp.py
```

---

### 方式三：使用 MCP CLI（如果可用）

```bash
# 安装 MCP CLI
npm install -g @modelcontextprotocol/cli

# 登录
mcp-publisher login github

# 发布
mcp-publisher publish
```

---

## 📊 验证发布

### 检查 Registry 状态

```bash
python check_registry.py
```

或访问：
- https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

### 在 Trae IDE 中使用

```bash
# 安装
mcp install io.github.Echoqili/ssh-licco

# 或在 MCP 配置中添加
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

---

## 🔧 故障排除

### 问题 1: 登录失败

**错误**: `401 Unauthorized`

**解决方案**:
- 检查 GITHUB_TOKEN 是否正确
- 确保 token 有 repo 权限
- token 可能已过期，重新生成

### 问题 2: 发布失败 - 版本已存在

**错误**: `400 Bad Request - version already exists`

**解决方案**:
- 升级版本号到 0.1.8
- 或等待 Registry 同步完成

### 问题 3: README 验证失败

**错误**: `README must contain mcp-name marker`

**解决方案**:
确保 README.md 包含：
```markdown
<!-- mcp-name: io.github.Echoqili/ssh-licco -->
```

---

## 📝 完整发布流程总结

1. **准备阶段**
   - ✅ 更新 pyproject.toml 版本号
   - ✅ 确保 README 包含 mcp-name 标识
   - ✅ 提交代码到 GitHub

2. **发布 PyPI**
   - ✅ 创建 GitHub Release
   - ✅ GitHub Actions 自动发布到 PyPI

3. **发布 MCP Registry**
   - 🔄 运行发布脚本或 Workflow
   - 🔄 验证发布成功

4. **验证**
   - 🔄 检查 Registry API
   - 🔄 在 Trae IDE 中测试安装

---

## 🔗 相关资源

- **MCP Registry**: https://registry.modelcontextprotocol.io/
- **MCP 文档**: https://modelcontextprotocol.io/docs
- **GitHub Repo**: https://github.com/Echoqili/ssh-licco
- **PyPI**: https://pypi.org/project/ssh-licco/

---

## 🎉 下一步

发布完成后，你的 MCP 服务器将：
1. ✅ 在 MCP Registry 中可查
2. ✅ 可通过 `mcp install` 命令安装
3. ✅ 在 Trae IDE 的 MCP Market 中显示（可能需要等待索引）
4. ✅ 对全球开发者可见

---

*Last updated: 2026-03-11*
*Version: 0.1.7*
