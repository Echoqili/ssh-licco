# MCP Registry 发布状态说明

## 📊 当前状态

### ✅ 已完成的发布

1. **PyPI 发布**
   - 版本：0.1.3
   - 状态：✅ 成功
   - 链接：https://pypi.org/project/ssh-licco/0.1.3/

2. **GitHub Release**
   - 版本：v0.1.3
   - 状态：✅ 成功
   - 链接：https://github.com/Echoqili/ssh-licco/releases/tag/v0.1.3

3. **MCP Registry API**
   - 状态：✅ 已发布到 registry
   - API 验证：通过
   - 问题：服务器名称显示为 `None`

---

## ❓ 为什么 MCP 市场看不到？

### 原因分析

1. **MCP Registry ≠ MCP Marketplace**
   - MCP Registry 是一个 API 服务
   - 目前没有官方的 Web UI 市场
   - 开发者通过 API 或命令行工具访问

2. **服务器名称格式问题**
   - API 返回的服务器名称为 `None`
   - 可能是命名空间格式不正确
   - 需要使用正确的格式：`io.github.Echoqili/ssh-licco`

3. **索引延迟**
   - Registry 需要时间索引新发布的服务器
   - 通常需要 5-30 分钟

---

## 🔍 如何验证发布成功？

### 方法 1：使用 API 检查

```bash
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.Echoqili/ssh-licco"
```

### 方法 2：使用 MCP CLI

```bash
# 安装 MCP CLI
npm install -g @modelcontextprotocol/cli

# 搜索服务器
mcp search ssh-licco

# 安装服务器
mcp install io.github.Echoqili/ssh-licco
```

### 方法 3：直接使用

```bash
# 如果已经知道服务器名称，可以直接安装
mcp install ssh-licco
```

---

## 📝 正确的发布流程总结

### 1. 准备阶段
```bash
# 更新版本号
pyproject.toml: version = "0.1.3"

# 添加 mcp-name 标识到 README
<!-- mcp-name: io.github.Echoqili/ssh-licco -->
```

### 2. 发布到 PyPI
```bash
# 创建 GitHub Release（自动触发 PyPI 发布）
git tag v0.1.3
git push --tags

# 或使用 GitHub Actions 自动发布
```

### 3. 发布到 MCP Registry
```bash
# 使用 MCP Publisher CLI
mcp-publisher login github
mcp-publisher publish

# 或使用 API
POST https://registry.modelcontextprotocol.io/v0.1/publish
{
  "$schema": "...",
  "name": "io.github.Echoqili/ssh-licco",
  "version": "0.1.3",
  ...
}
```

---

## 🎯 重要发现

### MCP 生态系统现状

1. **没有中央市场 UI**
   - MCP 官方没有提供类似 PyPI.org 的网站
   - 服务器列表在 GitHub 维护
   - 主要通过 CLI 工具访问

2. **访问方式**
   - 命令行：`mcp install <server-name>`
   - API: `https://registry.modelcontextprotocol.io/v0/servers`
   - GitHub: https://github.com/modelcontextprotocol/servers

3. **命名规范**
   - 格式：`io.github.<username>/<repo>`
   - 或：`io.pypi.<package-name>`

---

## ✅ 验证清单

- [x] PyPI 包可用
- [x] GitHub Release 创建
- [x] MCP Registry API 发布成功
- [x] README 包含 mcp-name 标识
- [ ] MCP CLI 可以安装
- [ ] 服务器名称正确显示

---

## 🔧 下一步

1. **等待索引完成**
   - 等待 30 分钟
   - 再次检查 API

2. **使用 MCP CLI 测试**
   ```bash
   mcp install io.github.Echoqili/ssh-licco
   ```

3. **如果仍然看不到**
   - 检查服务器名称格式
   - 考虑重新发布
   - 联系 MCP 支持

---

## 📚 相关资源

- MCP Registry API: https://registry.modelcontextprotocol.io/
- MCP GitHub: https://github.com/modelcontextprotocol
- MCP 文档：https://modelcontextprotocol.io/
- PyPI 包：https://pypi.org/project/ssh-licco/

---

*Last updated: 2026-03-08*
*Version: 0.1.3*
*Status: Published to Registry, waiting for indexing*
