# OpenSpec 开发指南

> 基于 OpenSpec 的规范驱动开发（Spec-Driven Development）工作流指南。

---

## 目录

- [概述](#概述)
- [工作流概览](#工作流概览)
- [快速开始：发起一个变更](#快速开始发起一个变更)
- [变更生命周期](#变更生命周期)
- [常用命令](#常用命令)
- [项目中的 OpenSpec 配置](#项目中的-openspec-配置)
- [完整操作案例](#完整操作案例)
- [最佳实践](#最佳实践)

---

## 概述

OpenSpec 是一个 AI-native 的规范驱动开发系统。ssh-licco 使用 OpenSpec 的 `spec-driven` 工作流来管理功能开发和变更追踪。

规范文件位于 `openspec/specs/` 目录，定义了项目的所有能力域（capabilities）。

---

## 工作流概览

```
Propose（提议）
    ↓
Specs（规范）
    ↓
Design（设计）
    ↓
Tasks（任务）
    ↓
Apply（实现）
    ↓
Archive（归档）
```

### 工件说明

| 工件 | 文件名 | 描述 |
|------|--------|------|
| **Proposal** | `proposal.md` | WHY — 为什么做这个变更，实现什么能力 |
| **Specs** | `specs/<name>/spec.md` | WHAT — 每个能力域的需求和场景规范 |
| **Design** | `design.md` | HOW — 技术设计和架构决策 |
| **Tasks** | `tasks.md` | DO — 可追踪的 checklist 实现任务 |

---

## 快速开始：发起一个变更

### 方式一：通过 AI 助手（推荐）

在对话中直接描述你想要开发的功能：

```
我想添加 SCP 文件传输支持
```

AI 助手会自动启动 Propose 流程，生成 proposal、design、tasks 等工件。

你也可以在对话中使用快捷命令：

| 命令 | 作用 |
|------|------|
| `/opsx:propose` | 发起新变更（生成 proposal → specs → design → tasks） |
| `/opsx:apply` | 按 tasks.md 逐个实现任务 |
| `/opsx:explore` | 进入探索模式，梳理需求 |

### 方式二：手动创建

```bash
# 1. 创建变更目录
openspec new change "<change-name>" --description "变更描述"

# 2. 创建 proposal
# 编辑 openspec/changes/<change-name>/proposal.md

# 3. 创建 specs（每个能力创建一个 spec 文件）
# 编辑 openspec/changes/<change-name>/specs/<capability>/spec.md

# 4. 创建 design
# 编辑 openspec/changes/<change-name>/design.md

# 5. 创建 tasks
# 编辑 openspec/changes/<change-name>/tasks.md
```

---

## 变更生命周期

### 1. Propose — 提议阶段

**目标：** 定义变更的背景、范围和能力域。

在 proposal 中明确：
- **Why** — 解决什么问题
- **What Changes** — 具体变更列表
- **Capabilities** — 新增/修改的能力域（每个能力会生成对应的 spec）
- **Impact** — 影响范围

### 2. Specs — 规范阶段

**目标：** 为每个能力域编写详细规范。

每个 spec 包含：
- **Requirement** — 需求描述，使用 SHALL/MUST 等规范性用语
- **Scenario** — GIVEN/WHEN/THEN 格式的场景测试用例

规范文件位于 `openspec/changes/<change-name>/specs/<capability>/spec.md`。

### 3. Design — 设计阶段

**目标：** 记录技术实现方案。

包含：
- **Context** — 背景和现有状态
- **Goals / Non-Goals** — 设计目标和排除范围
- **Decisions** — 关键决策及其理由（如：为什么选 X 而非 Y）
- **Risks / Trade-offs** — 已知风险和权衡

### 4. Tasks — 任务阶段

**目标：** 将设计拆分为可执行的实现任务。

任务格式：
```markdown
## N. 任务组名

- [ ] N.1 任务描述
- [ ] N.2 任务描述
```

每个任务应足够小，可在一个开发会话中完成。

### 5. Apply — 实现阶段

按 tasks.md 中的顺序逐个实现任务。AI 助手会跟踪进度并更新任务状态。

查看进度：
```bash
openspec status --change "<change-name>"
```

### 6. Archive — 归档阶段

变更实现完成后归档到 `openspec/changes/archive/`：

```bash
openspec archive <change-name>
```

归档后变更不再显示在活跃列表中，但所有工件保留供将来参考。

---

## 常用命令

### 变更管理

```bash
# 列出所有活跃变更
openspec list

# 列出所有规范
openspec list --specs

# 查看变更状态
openspec status --change "<change-name>"

# 查看变更状态（JSON 格式）
openspec status --change "<change-name>" --json

# 查看变更详情
openspec show "<change-name>"

# 验证变更完整性
openspec validate "<change-name>"
```

### 工件操作

```bash
# 获取工件创建指令
openspec instructions <artifact-id> --change "<change-name>"

# 获取 apply 实现指令
openspec instructions apply --change "<change-name>"

# 查看工件模板路径
openspec templates --change "<change-name>"
```

### 全局操作

```bash
# 查看 OpenSpec 配置
openspec config

# 提交反馈
openspec feedback "<message>"
```

---

## 项目中的 OpenSpec 配置

### 项目级配置：`openspec/config.yaml`

```yaml
schema: spec-driven
context: |
  Tech stack: Python 3.10+, asyncssh, mcp SDK, pydantic
  Project: ssh-licco - SSH MCP Server for AI models
  Repository: https://github.com/Echoqili/ssh-licco
```

包含技术栈、项目描述、代码规范等上下文信息。

### 项目规范：`openspec/specs/`

当前定义了 6 个能力域：

| 规范 | 需求数 | 描述 |
|------|--------|------|
| `ssh-connection` | 4 | 连接管理、认证、优先级解析 |
| `ssh-command-execution` | 6 | 命令执行、安全验证、后台任务 |
| `ssh-session-management` | 6 | 会话生命周期、保活、超时 |
| `ssh-file-transfer` | 4 | SFTP 上传、下载、目录列表 |
| `ssh-docker-management` | 3 | Docker 构建、状态、日志 |
| `ssh-security` | 6 | 命令验证、速率限制、审计日志 |

### 已归档变更

已实现的变更归档在 `openspec/changes/archive/`：

| 归档 | 日期 | 描述 |
|------|------|------|
| `2026-06-01-ssh-mcp-implementation` | 2026-06-01 | SSH MCP 服务器完整实现（46 个任务） |

---

## 完整操作案例

以下以一个真实的开发流程为例，展示 OpenSpec 的完整使用过程。

### 案例背景

将 SSH MCP 服务的全部功能（连接、命令执行、会话管理、文件传输、Docker 管理、安全等）通过 OpenSpec 规范驱动开发流程进行管理和追踪，共涉及 **6 个能力域、46 个实现任务**。

### 阶段一：Propose — 发起变更

开发者提出需求后，AI 创建变更并生成 proposal。

**命令：**
```bash
openspec new change "ssh-mcp-implementation" \
  --description "SSH MCP Server full implementation"
```

**生成的 proposal.md：**
```markdown
## Why

实现完整的 SSH MCP 服务器工具集，提供全面的远程服务器管理能力。

## What Changes

- 实现 SSH 连接管理（密码/密钥/Agent 认证）
- 添加命令执行（安全验证、后台执行、超时控制）
- 添加会话生命周期管理
- 添加 SFTP 文件传输
- 添加 Docker 容器管理
- 添加 SSH 密钥对生成
- 实现安全特性（命令验证、速率限制、审计日志）

## Capabilities

### New Capabilities
- `ssh-connection`: SSH 连接管理与认证
- `ssh-command-execution`: 远程命令执行与安全验证
- `ssh-session-management`: 会话生命周期与保活
- `ssh-file-transfer`: SFTP 文件传输
- `ssh-docker-management`: Docker 容器管理
- `ssh-security`: 安全验证与防护
```

### 阶段二：查看工件状态

每次创建完一个工件后，检查依赖是否就绪：

```bash
openspec status --change "ssh-mcp-implementation" --json
```

输出显示了工件的依赖链：

```
proposal (ready) → design (blocked, needs proposal)
                 → specs (blocked, needs proposal)
                 → tasks (blocked, needs design + specs)
```

### 阶段三：创建 Design — 设计文档

获取 design 的创建指令，参考已有代码编写技术方案：

```bash
openspec instructions design --change "ssh-mcp-implementation" --json
```

**生成的 design.md 关键内容：**
```markdown
## Decisions

- Paramiko as SSH client: 选择 paramiko 而非 asyncssh，因为同步 API 更适合
  线程池执行器模式
- ThreadPoolExecutor 封装: 将 paramiko 的阻塞 API 通过线程池接入 asyncio
- Session-based 架构: 每个连接封装为 SSHSession，SessionManager 统一管理
- 安全级别: SSH_SECURITY_LEVEL 控制严格程度（strict/balanced/relaxed）
- 配置优先级: 用户参数 > 命名主机 > 环境变量

## Risks / Trade-offs

- 基于命令的 Docker 集成不如 SDK 方式类型安全
- 模式匹配的后台检测可能遗漏边缘场景
```

### 阶段四：关联 Specs — 规范文件

项目已有 6 个规范文件位于 `openspec/specs/`，将其复制到变更目录下：

```bash
# specs 工件路径为 specs/**/*.md，需将规范文件放入变更目录
cp -r openspec/specs/* openspec/changes/ssh-mcp-implementation/specs/
```

验证状态：

```bash
openspec status --change "ssh-mcp-implementation"
```

输出：

```
[x] proposal
[x] design
[x] specs
[ ] tasks
```

### 阶段五：创建 Tasks — 任务清单

获取 tasks 创建指令并按模板编写：

```bash
openspec instructions tasks --change "ssh-mcp-implementation" --json
```

**生成的 tasks.md（节选）：**
```markdown
## 1. Project Setup

- [x] 1.1 Initialize project structure with pyproject.toml
- [x] 1.2 Add dependencies (paramiko, mcp, pydantic)
- [x] 1.3 Create config directory with hosts.json

## 2. SSH Connection

- [x] 2.1 Implement connection configuration and priority resolution
- [x] 2.2 Implement password authentication
- [x] 2.3 Implement private key authentication
...

## 9. Security

- [x] 9.1 Implement CommandValidator with whitelist
- [x] 9.2 Implement three security levels
- [x] 9.3 Implement dangerous pattern detection
- [x] 9.4 Implement PathValidator
- [x] 9.5 Implement rate limiting
- [x] 9.6 Implement audit logging
```

全部工件完成后，状态变为：

```
[x] proposal
[x] design
[x] specs
[x] tasks

isComplete: true
```

### 阶段六：Apply — 实现任务

通过 apply 指令查看任务进度并按顺序实现：

```bash
openspec instructions apply --change "ssh-mcp-implementation" --json
```

输出显示 46/46 任务全部完成（因为代码已在创建变更前实现）：

```json
{
  "state": "all_done",
  "progress": { "total": 46, "complete": 46, "remaining": 0 }
}
```

如果是有未完成任务的变更，AI 会逐个任务实现并更新 tasks.md 中的 checkbox：

```markdown
- [ ] 2.1 实现功能A
- [x] 2.2 实现功能B  ← 完成一个就标记一个
```

### 阶段七：Archive — 归档变更

实现完成后归档，保留所有工件供将来参考：

```bash
# 确认全部完成
openspec status --change "ssh-mcp-implementation"

# 归档
openspec archive ssh-mcp-implementation
```

归档后变更移至 `openspec/changes/archive/2026-06-01-ssh-mcp-implementation/`。

**验证归档结果：**
```bash
openspec list --json
# 输出: {"changes":[]}  ← 活跃变更列表为空
```

---

## 最佳实践

1. **从小变更开始** — 每个变更聚焦一个功能点，避免大而全
2. **场景先行** — 在 spec 中用 GIVEN/WHEN/THEN 写清楚验收条件
3. **设计要记录决策** — 写清楚"为什么选 A 不选 B"，方便后续维护者理解
4. **任务要可验证** — 每个任务完成后应能明确知道"做完了"
5. **及时归档** — 变更实现完成后立即归档，保持活跃列表整洁
6. **保持 spec 更新** — 如果实现过程中发现 spec 不合理，及时更新 spec

---

*Last updated: 2026-06-01*