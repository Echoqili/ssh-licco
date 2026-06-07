# OpenSpec 开发工作流 Skill

## 技能概述

OpenSpec 是基于规范驱动开发（Spec-Driven Development）的工作流系统。ssh-licco 使用 OpenSpec 来管理功能开发和变更追踪，确保每个功能都有清晰的提案、规范、设计和任务。

---

## 工作流概览

```
Propose（提议）
    ↓
Specs（规范） — 定义 WHAT
    ↓
Design（设计） — 定义 HOW
    ↓
Tasks（任务） — 定义 DO
    ↓
Apply（实现）
    ↓
Archive（归档）
```

---

## 快捷命令

在 Trae/IDE 对话中可以直接使用以下命令：

| 命令 | 功能 | 说明 |
|------|------|------|
| `/opsx:propose` | 发起新变更 | 自动生成 proposal、design、tasks 等工件 |
| `/opsx:apply` | 实现变更 | 按 tasks.md 逐个实现，跟踪进度 |
| `/opsx:explore` | 探索模式 | 梳理需求、分析问题、澄清需求 |
| `/opsx:archive` | 归档变更 | 实现完成后归档到 archive 目录 |

---

## Propose — 发起变更

当你有一个新功能或改进想法时：

1. **直接描述需求** — 告诉 AI 你想做什么
2. **AI 创建变更** — 自动生成 `openspec/changes/<name>/` 目录
3. **创建工件** — 按依赖顺序生成：
   - `proposal.md` — 为什么做这个变更
   - `design.md` — 技术设计方案
   - `tasks.md` — 实现任务列表
4. **关联现有规范** — 自动引用 `openspec/specs/` 中的已有规范

**产出：** 变更目录包含所有工件，可通过 `openspec status --change <name>` 查看状态。

---

## Apply — 实现变更

当变更已创建、tasks 已就绪时：

1. **启动实现** — AI 读取 tasks.md，从第一个未完成的任务开始
2. **逐个实现** — 每个任务完成后更新 checkbox：`- [ ]` → `- [x]`
3. **遇到阻塞** — 如果任务不清晰或遇到问题，暂停并询问
4. **完成提示** — 全部 46/46 任务完成后，提示归档

**进度查看：**
```bash
openspec status --change "<change-name>"
```

---

## Archive — 归档变更

变更实现完成后：

1. 检查所有工件状态（必须是 `done`）
2. 检查所有任务状态（必须全部 `[x]`）
3. 评估 delta spec 是否需要同步
4. 移动到 `openspec/changes/archive/YYYY-MM-DD-<name>/`
5. 从活跃变更列表中移除

**命令：**
```bash
openspec archive <change-name>
```

---

## 项目 OpenSpec 配置

### 配置文件

| 文件 | 说明 |
|------|------|
| `openspec/config.yaml` | 项目级 OpenSpec 配置（schema、context、rules） |
| `openspec/specs/` | 项目规范目录（6 个能力域） |
| `openspec/changes/` | 活跃变更目录 |
| `openspec/changes/archive/` | 已归档变更目录 |

### 已有规范

| 规范 | 需求数 | 描述 |
|------|--------|------|
| `ssh-connection` | 4 | 连接管理、认证、优先级解析 |
| `ssh-command-execution` | 6 | 命令执行、安全验证、后台任务 |
| `ssh-session-management` | 6 | 会话生命周期、保活、超时 |
| `ssh-file-transfer` | 4 | SFTP 上传、下载、目录列表 |
| `ssh-docker-management` | 3 | Docker 构建、状态、日志 |
| `ssh-security` | 6 | 命令验证、速率限制、审计日志 |

### 已归档变更

- `2026-06-01-ssh-mcp-implementation` — SSH MCP 服务器完整实现（46 个任务）

---

## 详细参考

- [docs/OPENSPEC_GUIDE.md](../OPENSPEC_GUIDE.md) — OpenSpec 使用指南
- `openspec/config.yaml` — 项目级 OpenSpec 配置
- `.trae/skills/openspec-propose/SKILL.md` — Propose skill 详情
- `.trae/skills/openspec-apply-change/SKILL.md` — Apply skill 详情
- `.trae/skills/openspec-archive-change/SKILL.md` — Archive skill 详情

---

*Last updated: 2026-06-01*