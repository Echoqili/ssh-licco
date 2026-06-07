---
name: openspec-workflow
description: Complete OpenSpec spec-driven development workflow. Guides feature development from proposal through design, tasks, implementation, and archival.
license: MIT
compatibility: Requires openspec CLI
metadata:
  author: ssh-licco
  version: "1.0"
---

# OpenSpec 规范驱动开发工作流

ssh-licco 使用 OpenSpec 的 `spec-driven` 工作流管理功能开发。

## 工作流概览

```
Propose → Specs → Design → Tasks → Apply → Archive
```

## 核心命令快捷方式

在对话中可以使用以下命令启动对应流程：

| 命令 | 作用 |
|------|------|
| `/opsx:propose` | 发起新变更，生成 proposal/design/tasks |
| `/opsx:apply` | 按 tasks 实现当前变更 |
| `/opsx:explore` | 进入探索模式，梳理需求和分析问题 |
| `/opsx:archive` | 归档已完成的变更 |

## 工作流各阶段

### 阶段 1：Propose（提议）

用户描述需求后，AI 助手通过 `openspec-propose` skill 创建：

- `proposal.md` — WHY：变更动机、能力域、影响范围
- `design.md` — HOW：技术架构、设计决策
- `tasks.md` — DO：checklist 实现任务
- 关联已有的 `openspec/specs/` 规范文件

**产出检查：** `openspec status --change "<name>"` 显示 `isComplete: true`

### 阶段 2：Apply（实现）

通过 `openspec-apply-change` skill 按 tasks.md 逐个实现：

- 从第一个未完成的任务开始
- 每次实现一个任务，然后标记为 `[x]`
- 遇到阻塞或不确定时暂停并询问用户
- 全部完成后提示归档

**命令：**
```bash
# 查看实现进度
openspec instructions apply --change "<change-name>" --json

# 查看变更状态
openspec status --change "<change-name>"
```

### 阶段 3：Archive（归档）

通过 `openspec-archive-change` skill 归档已完成变更：

- 检查工件和任务完成状态
- 评估 delta spec 同步
- 迁移到 `openspec/changes/archive/YYYY-MM-DD-<name>/`

**命令：**
```bash
openspec archive <change-name>
```

## 项目当前状态

### 已归档变更

| 归档 | 日期 | 任务数 |
|------|------|--------|
| `2026-06-01-ssh-mcp-implementation` | 2026-06-01 | 46 |

### 现有规范（openspec/specs/）

- `ssh-connection` — 4 需求
- `ssh-command-execution` — 6 需求
- `ssh-session-management` — 6 需求
- `ssh-file-transfer` — 4 需求
- `ssh-docker-management` — 3 需求
- `ssh-security` — 6 需求

## 参考

- 完整指南：[docs/OPENSPEC_GUIDE.md](file:///d:/pyworkplace/ssh-mcp/docs/OPENSPEC_GUIDE.md)
- 项目配置：`openspec/config.yaml`