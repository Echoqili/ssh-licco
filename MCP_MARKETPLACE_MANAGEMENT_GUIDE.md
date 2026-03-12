# 🎯 MCP Marketplace 认领后管理完整指南

## 📋 目录

1. [认领步骤](#认领步骤)
2. [管理后台介绍](#管理后台介绍)
3. [完善 Listing 信息](#完善-listing-信息)
4. [数据分析](#数据分析)
5. [用户互动](#用户互动)
6. [版本更新](#版本更新)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

---

## 🚀 认领步骤

### 步骤 1：点击认领按钮

1. **打开邮件**
   - 找到来自 MCP Marketplace 的邮件
   - 主题："Your MCP server is already listed on MCP Marketplace"

2. **点击 "Claim your listing →"**
   - 绿色按钮
   - 会跳转到 MCP Marketplace 网站

### 步骤 2：GitHub 登录

1. **选择登录方式**
   - 点击 "Sign in with GitHub"

2. **授权**
   - 审查权限请求
   - 点击 "Authorize MCP Marketplace"

3. **自动转移**
   - listing 会自动转移到你的 GitHub 账户
   - 成为认证作者（显示 Verified 徽章）

### 步骤 3：确认成功

认领成功后会看到：
- ✅ "Listing claimed successfully!"
- ✅ 你的 GitHub 头像显示为作者
- ✅ 获得管理后台访问权限

---

## 🎛️ 管理后台介绍

### 访问管理后台

**URL**: https://mcp-marketplace.io/dashboard

### 主要功能区域

#### 1. **Overview（概览）**
- 安装量统计
- 访问量统计
- 最近活动
- 快速操作

#### 2. **Listings（列表管理）**
- 查看所有 listing
- 编辑信息
- 上下架控制

#### 3. **Analytics（数据分析）**
- 安装趋势
- 地理分布
- 来源分析
- 用户行为

#### 4. **Reviews（评论管理）**
- 查看用户评价
- 回复评论
- 处理反馈

#### 5. **Settings（设置）**
- 账户设置
- 通知设置
- 支付信息（如有付费版本）

---

## ✏️ 完善 Listing 信息

### 基本信息编辑

#### 1. **标题和描述**

**当前信息：**
- Name: ssh-licco
- Description: SSH Model Context Protocol Server - Enable SSH functionality for AI models

**优化建议：**

```markdown
Name: ssh-licco - SSH MCP Server for AI Assistants

Description: 
🚀 Control SSH servers with natural language! 

Enable your AI assistant to execute commands, manage files, 
monitor logs, and deploy applications on remote servers via SSH.

✨ Key Features:
- 🎯 Natural language SSH control
- 🔐 Multiple auth methods (password, key, agent)
- 🔗 Long connection with auto keepalive
- 📦 SFTP file transfer
- 🐳 Docker support
- 📊 Batch execution across multiple servers
- 🛡️ Complete audit logging

⭐ Trusted by developers worldwide!
```

#### 2. **分类和标签**

**Categories:**
- ✅ Development
- ✅ DevOps
- ✅ Security（可选）

**Tags:**
```
ssh, mcp, ai, automation, devops, remote-access, 
security, file-transfer, docker, batch-execution, 
natural-language, ai-assistant, server-management
```

#### 3. **链接信息**

**必填链接：**
- **Homepage**: https://github.com/Echoqili/ssh-licco
- **Repository**: https://github.com/Echoqili/ssh-licco
- **Bug Tracker**: https://github.com/Echoqili/ssh-licco/issues
- **Documentation**: https://github.com/Echoqili/ssh-licco#readme

**可选链接：**
- **Discord/Community**: （如有）
- **Twitter**: （如有）

#### 4. **Logo 和截图**

**Logo 建议：**
- 尺寸：512x512 px
- 格式：PNG 或 SVG
- 建议：使用 SSH 相关图标

**截图建议：**
1. 终端执行示例
2. 文件传输界面
3. Docker 构建示例
4. 批量执行结果

**上传方法：**
1. 进入 Listings → Edit
2. 找到 Media 部分
3. 上传 Logo 和 Screenshots

---

## 📊 数据分析

### 关键指标

#### 1. **安装量（Installs）**

**指标说明：**
- Total Installs: 总安装量
- Daily Installs: 日均安装量
- Install Trend: 安装趋势（上升/下降）

**如何查看：**
- Dashboard → Analytics → Installs

**优化建议：**
- 安装量下降时检查：
  - 是否有负面评论
  - 竞争对手动态
  - 更新描述和标签

#### 2. **访问量（Views）**

**指标说明：**
- Page Views: 页面访问量
- Unique Visitors: 独立访客
- View to Install Rate: 访问转化率

**如何查看：**
- Dashboard → Analytics → Views

**优化建议：**
- 转化率低时优化：
  - 改进描述
  - 添加截图
  - 增加社会证明（评价、star 数）

#### 3. **地理分布**

**指标说明：**
- 用户来源国家/地区
- 主要市场分布

**如何查看：**
- Dashboard → Analytics → Geography

**用途：**
- 决定文档语言
- 确定推广重点地区
- 安排在线时间

#### 4. **来源分析**

**指标说明：**
- 流量来源（GitHub, Google, 直接访问等）
- 推荐网站

**如何查看：**
- Dashboard → Analytics → Sources

**优化建议：**
- 加强高转化渠道
- 在 GitHub README 添加链接
- 社交媒体推广

---

## 💬 用户互动

### 评论管理

#### 1. **查看新评论**

**通知方式：**
- 邮件通知（需开启）
- Dashboard 提醒
- 定期检查

**查看位置：**
- Dashboard → Reviews

#### 2. **回复评论**

**回复模板：**

**好评回复：**
```markdown
Thank you for your positive feedback! 🎉

We're thrilled that ssh-licco is helping you manage servers efficiently. 
If you need any assistance or have feature requests, feel free to:
- Open an issue on GitHub
- Join our Discord community

Happy coding! 🚀
```

**问题反馈回复：**
```markdown
Thanks for reporting this issue! 🔍

We take all feedback seriously. To help us investigate:
1. Could you provide more details about your setup?
2. Please check the troubleshooting guide: [link]
3. Feel free to open an issue on GitHub with logs

We'll work on a fix ASAP! 💪
```

**功能请求回复：**
```markdown
Great suggestion! 💡

This feature would indeed be valuable. I've:
1. Created a GitHub issue to track this: [link]
2. Added it to our roadmap for next month

Stay tuned for updates! 🔔
```

#### 3. **处理负面评价**

**处理步骤：**
1. **冷静回应** - 不要情绪化
2. **了解问题** - 询问详细信息
3. **提供解决方案** - 给出具体帮助
4. **跟进修复** - 更新后通知用户

**回复模板：**
```markdown
I'm sorry to hear about your experience 😔

We'd love to make this right. Could you please:
1. Share more details about the issue you encountered?
2. Check our documentation: [link]
3. Open a GitHub issue so we can investigate?

We're committed to improving ssh-licco and value your feedback! 🙏
```

---

## 🔄 版本更新

### 发布新版本

#### 1. **更新 PyPI 包**

```bash
# 1. 更新版本号
# 编辑 pyproject.toml: version = "0.1.8"

# 2. 提交代码
git add pyproject.toml
git commit -m "chore: bump version to 0.1.8"

# 3. 创建 tag
git tag v0.1.8
git push origin v0.1.8

# 4. GitHub Actions 自动发布到 PyPI
```

#### 2. **更新 MCP Registry**

```bash
# 运行发布脚本
python publish_now.py
```

#### 3. **更新 Marketplace**

**自动同步：**
- MCP Marketplace 会自动从 Registry 同步

**手动更新：**
1. Dashboard → Listings → Edit
2. 更新版本信息
3. 更新 changelog
4. 点击 Save

### 更新 Changelog

**模板：**

```markdown
## v0.1.8 (2026-03-12)

### 🎉 New Features
- Added support for SSH agent forwarding
- Implemented connection pooling for better performance

### 🐛 Bug Fixes
- Fixed connection timeout issue on Windows
- Resolved file transfer encoding problem

### 📝 Documentation
- Added Chinese documentation
- Improved installation guide

### ⚙️ Technical Updates
- Upgraded AsyncSSH to v2.18.0
- Improved error handling and logging
```

---

## 🎯 最佳实践

### 日常维护

#### 每天（5 分钟）

- ✅ 检查新评论
- ✅ 回复用户问题
- ✅ 查看安装量变化

#### 每周（30 分钟）

- ✅ 分析数据趋势
- ✅ 检查错误报告
- ✅ 更新文档（如有需要）
- ✅ 社交媒体推广

#### 每月（2 小时）

- ✅ 发布小版本更新
- ✅ 审查和优化 listing
- ✅ 分析竞争对手
- ✅ 规划新功能

### 推广策略

#### 1. **GitHub 推广**

- 在 README 添加 Marketplace 链接
- 添加 "Available on MCP Marketplace" 徽章
- 鼓励用户评价

**徽章代码：**
```markdown
[![MCP Marketplace](https://img.shields.io/badge/MCP-Marketplace-green.svg)](https://mcp-marketplace.io/servers/io.github.Echoqili/ssh-licco)
```

#### 2. **社交媒体**

- Twitter/X: 发布更新和功能
- LinkedIn: 分享技术文章
- Reddit: 参与 r/devops, r/programming
- Discord: 加入相关服务器

#### 3. **内容营销**

- 撰写使用教程
- 录制演示视频
- 参与播客访谈
- 在技术大会分享

#### 4. **社区建设**

- 创建 Discord 服务器
- 定期 AMA (Ask Me Anything)
- 举办线上活动
- 建立贡献者计划

---

## ❓ 常见问题

### Q1: 如何删除 listing？

**A:**
1. Dashboard → Settings
2. 找到 "Delete Listing"
3. 确认删除
4. 或联系 support 协助

### Q2: 可以转移所有权吗？

**A:**
- 可以！
- Settings → Transfer Ownership
- 输入新所有者的 GitHub 用户名
- 对方接受后完成转移

### Q3: 如何设置付费版本？

**A:**
1. Dashboard → Pricing
2. 选择定价模式（一次性/订阅）
3. 设置价格
4. 添加支付信息
5. 提交审核

### Q4: 可以下架后再上架吗？

**A:**
- 可以！
- Listings → 选择下架
- 需要时重新上架
- 数据会保留

### Q5: 如何查看谁安装了？

**A:**
- 出于隐私，看不到具体用户
- 只能看到统计数据
- 安装量、地区分布等

### Q6: 评论可以删除吗？

**A:**
- 不能直接删除
- 可以举报不当评论
- 平台会审核处理
- 建议公开回复解释

### Q7: 如何合并重复 listing？

**A:**
1. 联系 support: support@mcp-marketplace.io
2. 提供两个 listing 的链接
3. 说明哪个是主 listing
4. 等待后台合并

### Q8: 数据多久更新一次？

**A:**
- 安装量：实时更新
- 访问量：每小时更新
- 地理分布：每天更新
- 趋势图：每周更新

---

## 📞 获取帮助

### 官方支持

- **Email**: support@mcp-marketplace.io
- **Discord**: 邮件中有链接
- **Documentation**: https://mcp-marketplace.io/docs

### 社区资源

- **GitHub Discussions**: MCP Marketplace 讨论区
- **Reddit**: r/MCP
- **Twitter**: @MCPMarketplace

---

## 🎊 总结

### 认领后检查清单

- [ ] 点击邮件中的 "Claim your listing"
- [ ] GitHub 登录授权
- [ ] 确认获得 Verified 徽章
- [ ] 完善描述和信息
- [ ] 上传 Logo 和截图
- [ ] 设置通知偏好
- [ ] 查看数据分析
- [ ] 回复现有评论
- [ ] 添加 GitHub README 链接
- [ ] 制定推广计划

### 成功指标

- 📈 安装量稳步增长
- ⭐ 评分 4.5+ 星
- 💬 积极回复用户评论
- 🔄 定期更新版本
- 🌟 社区活跃度提升

---

**记住：** 持续改进和与用户互动是成功的关键！

*Generated: 2026-03-12*  
*Version: 1.0*  
*Status: Ready for MCP Marketplace Management*
