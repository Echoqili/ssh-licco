# Changelog

本文件记录 SSH LICCO 项目的所有重要变更，遵循 [语义化版本规范](https://semver.org/lang/zh-CN/)。

---

## [2.3.1] - 2026-07-11

### 修复

- **生产配置限流 bug 修复**：`config/mcp.production-hardened.example.json` 中 `SSH_RATE_LIMIT=30` 被代码误读为布尔值 `"30".lower() == "true"` → `False`，导致限流在生产配置下实际为关闭状态。修正为 `SSH_RATE_LIMIT=true`（总开关）+ 新增 `SSH_RATE_LIMIT_MAX=30`（次数上限），两者分开配置。
- **删除 phantom env 变量**：
  - `SSH_STRICT_HOST_KEY_CHECKING` 在两个示例配置文件中均无对应代码读取（`ConnectionConfig.strict_host_key_checking` 字段由 `ssh_connect` 参数或 `hosts.json` 设置），从 `mcp.config.example.json` 与 `config/mcp.production-hardened.example.json` 移除。
  - `SSH_EXTRA_ALLOWED_PATTERNS` 同样无代码读取（`os.getenv` 0 命中），从 `docs/skills/ssh-mcp-setup/SKILL.md`、`.trae/skills/ssh-mcp-setup/SKILL.md`、`docs/skills/ssh-mcp-dev/SKILL.md`、`.trae/skills/ssh-mcp-dev/SKILL.md`、`docs/skills/ssh-mcp-troubleshoot/SKILL.md`、`.trae/skills/ssh-mcp-troubleshoot/SKILL.md` 移除。

### 文档

- `config/mcp.production-hardened.example.json`：加 `_notes` 块说明 `rate_limit_naming` 与 `host_key_checking` 配置去向。
- `docs/SECURITY_HARDENING.md`：环境变量速查从 11 项扩为 21+ 项完整表（按"安全与限流 / 加固点 1 / 加固点 2 / 加固点 3 / 加固点 4 / 默认连接参数"分组），并加"phantom 变量提示"；Checklist 删除已彻底废弃的 `SSH_APPROVAL_GATE` 提示。
- `README.md`：新增"完整环境变量速查（v2.3.0）"总表。
- 全部 4 个 SKILL.md（dev/setup/troubleshoot × docs/.trae 双份）补齐 `SSH_RATE_LIMIT` bool 类型说明，统一移除 `SSH_EXTRA_ALLOWED_PATTERNS`。

### 影响

- 已部署用户：使用 `config/mcp.production-hardened.example.json` 之前版本的，请同步更新 env 配置（`SSH_RATE_LIMIT=true` + `SSH_RATE_LIMIT_MAX=30`），否则限流实际未生效。
- 调试图：若之前依赖 `SSH_STRICT_HOST_KEY_CHECKING` env 变量来开关主机密钥检查（实际不生效），请改用 `ssh_connect` 工具的 `known_hosts_path` / `accept_new_host_key` 参数，或 `hosts.json` 的 `strict_host_key_checking` 字段。

---

## [2.3.0] - 2026-07-11

### 移除 ⚠️ BREAKING

- **删除 `SSH_APPROVAL_GATE` 审批方案全部代码**（v2.1.0 引入，v2.2.0 标记为废弃）：
  - 删除 `ssh_mcp/approval.py`（`ApprovalGate` 单例与 `ApprovalRecord` 数据类）
  - 删除 `ssh_mcp/handlers/approval.py`（`handle_request_approval` / `handle_approve_command` / `handle_list_approvals` 三个 MCP 工具 handler）
  - `ssh_mcp/handlers/__init__.py` 的 `HANDLERS` 注册表移除 3 个工具（共 12 → 9）
  - `ssh_mcp/handlers/utils.py` 移除 `check_approval_gate()` 函数
  - `ssh_mcp/handlers/execute.py` 移除 `check_approval_gate()` 调用与 `approval_id` 参数传递
  - `ssh_mcp/handlers/schemas.py` 移除 `approval_id` 输入参数 + 3 个 `ssh_request_approval` / `ssh_approve_command` / `ssh_list_approvals` Tool 定义
- **删除 3 个环境变量**（不再被代码读取，可从部署配置中移除）：
  - `SSH_APPROVAL_GATE`
  - `SSH_APPROVAL_STORE`
  - `SSH_APPROVAL_TTL`
- **删除原因**：审批流程依赖 AI 自报命令 + 运维人员背书，存在闭环风险（AI 可绕过审批构造看似无害的命令；运维侧背书流于形式）。v2.2.0 的"灾难性命令硬拦截"在 MCP 网关层直接拒绝灾难性模式，更安全更直接。

### 文档

- `MCP_CONFIG_GUIDE.md`：删除"## 🎯 使用场景配置"5 个角色化场景（Web / Python / DB / 系统管理员 / 生产），在没对接 MCP 网关前不做角色严格声明。
- `docs/SECURITY_HARDENING.md`：env 变量表移除 3 个废弃项；"v2.1.0 审批方案"小节改写为"已被删除"。
- `README.md`：2 处"保留作为参考"改为"已在 v2.2.0 删除"。
- `config/mcp.production-hardened.example.json`：移除 `_deprecated` 块，version 1.1.0 → 1.2.0。
- `.trae/documents/split-server-py-plan.md`：移除 approval.py 文件树项、迁移步骤、Tool count 12 → 9。

### 迁移指南

v2.2.x → v2.3.0：
- 删除部署配置中的 `SSH_APPROVAL_GATE` / `SSH_APPROVAL_STORE` / `SSH_APPROVAL_TTL` 环境变量
- 如有自定义脚本调用了 `ssh_request_approval` / `ssh_approve_command` / `ssh_list_approvals` 三个工具，请改用 v2.2.0 起的硬拦截机制——灾难性命令直接被 MCP 网关拒绝，无需审批流
- `approval_id` 入参已从 `ssh_execute` 的 inputSchema 移除，调用代码请删除该字段

---

## [2.2.0] - 2026-07-11

### 安全 ⚠️ BREAKING

- **硬拦截灾难性命令**：新增 `CommandValidator.HARD_BLOCKED_PATTERNS` 和 `CommandValidator.check_hard_block()`，对以下命令模式**无条件**拦截（任何安全级别、`confirm_dangerous`、`confirmation_layer` 均无法绕过）：
  - `rm -rf` 作用于绝对路径（包括 `/`、`/*`、`/path`、`/path/*`，`-fr` 变体同效）
  - `mkfs.*` 任意文件系统格式化
  - `dd if=/dev/(zero|random|urandom) of=/dev/(sd|nvme)` 覆写裸盘
  - bash fork-bomb（`:(){ :|:& };:` 及空白变体）
  - `chmod -R 777 /` / `chmod -R 000 /` 根目录递归改权限
  - `> /dev/(sd|nvme)` / `>> /dev/(sd|nvme)` 裸设备重定向
- `SecurityError` 新增 `hard_block: bool` 属性，handler 据此区分错误提示（不再误导用户尝试 `confirm_dangerous=true` 绕过）。
- 命中硬拦截时输出 `WARNING` 审计日志（含 category 与命令），便于 SOC 监控。
- 旧行为（依赖 `confirm_dangerous=true` 执行 `rm -rf /abs/path`）已不可行。如需清理绝对路径，请直接 SSH 登录服务器，或用 `mv <path> /tmp/.trash_<ts>/` 走 MCP。

---

## [2.1.1] - 2026-07-01

### 维护

- 代码风格统一：使用 `ruff format` 与 `ruff check --fix` 全量格式化，确保 lint 全部通过。
- 版本号对齐：`pyproject.toml` / `ssh_mcp/__init__.py` / `package.json` / `package-lock.json` 统一升级到 2.1.1。

---

## [2.1.0] - 2026-06-29

### 新增功能

- **生产加固四项**（SSH 跳板模式落地边界）：补齐跳板机单点风险，所有加固点默认关闭，向后兼容，生产显式开启。
  - **加固点 1 · 运行账号最小权限**：`ssh_mcp/runtime_guard.py`，进程入口校验非 root / 非 sudo / 账号白名单。开关 `SSH_RUNTIME_GUARD=true`。
  - **加固点 2 · 密钥不落地磁盘**：`ssh_mcp/secret_provider.py`（env/command/http 三 provider）+ `KeyManager.load_key_from_str()` 内存加载 + `save_key()` 拒绝落盘。私钥用 `bytearray` 持有，`release()` 清零，`atexit` 统一清理。开关 `SSH_SECRET_PROVIDER_ENABLED=true`。
  - **加固点 3 · 双层命令拦截**：第一层 `server._normalize_command_for_remote_guard()` 禁止 `| ; & $() \` > <` 元字符；第二层远端 ForceCommand 脚本 `config/remote-guard/ssh_licco_force_command.sh` + 白名单 + sshd_config 片段。开关 `SSH_REMOTE_GUARD=true`。
  - **加固点 4 · 高危操作审批**：`ssh_mcp/approval.py`（ApprovalGate，JSON 持久化，一次性消费，命令严格匹配，TTL 失效）。开关 `SSH_APPROVAL_GATE=true`。

- **新增 3 个 MCP 工具**（高危审批工作流）：
  - `ssh_request_approval` — AI 提交高危命令审批申请，返回 approval_id
  - `ssh_approve_command` — 运维人员人工审批（approved/rejected）
  - `ssh_list_approvals` — 列出待审批队列或全部历史

- **`ssh_execute` 新增参数**：
  - `approval_id` — 高危命令审批 ID（加固点 4）
  - `remote_guard` — 标记远端已启用 ForceCommand 二次校验（加固点 3）

- **`ConnectionConfig` 新增字段**：`private_key_material`（内存私钥 PEM，密钥不落地模式）

- **远端加固配置**：`config/remote-guard/` 提供 ForceCommand 脚本、白名单模板、sshd_config 示例

### 安全增强

- **运行身份守护**：拒绝 root / sudo 上下文启动 ssh-licco 进程，强制专用普通账号
- **私钥内存化**：连接建立后立即清零内存中的私钥字节，跳板机磁盘无私钥文件
- **命令逃逸防护**：远端 ForceCommand + 跳板机侧元字符规范化，关闭 shell 元字符绕过白名单的路径
- **高危命令人工闸门**：CRITICAL/HIGH 风险命令（rm -rf / reboot / iptables 等）必须经人工审批，AI 不能直接下发

### 新增文件

- `ssh_mcp/runtime_guard.py` — 运行账号最小权限守护
- `ssh_mcp/secret_provider.py` — 密钥不落地凭证管理（SecretManager + 3 种 provider）
- `ssh_mcp/approval.py` — 高危操作审批门禁（ApprovalGate）
- `config/remote-guard/ssh_licco_force_command.sh` — 远端 ForceCommand 二次校验脚本
- `config/remote-guard/allowed_commands.txt` — 远端命令白名单模板
- `config/remote-guard/sshd_config.example` — sshd Match User 配置示例
- `docs/SECURITY_HARDENING.md` — 完整加固方案文档
- `test_hardening.py` — 四项加固端到端验收测试（4/4 通过）

### 修改的文件

- `ssh_mcp/server.py` — `run_server()` 接入 runtime_guard；`_handle_connect` 接入 SecretManager；`_handle_execute` 接入 remote_guard 规范化 + approval gate；新增 3 个审批工具的 handler 与 schema；`ssh_execute` schema 新增 `approval_id` / `remote_guard` 参数
- `ssh_mcp/key_manager.py` — 新增 `load_key_from_str()`；`save_key()` 在密钥不落地模式拒绝落盘
- `ssh_mcp/connection_config.py` — 新增 `private_key_material` 字段，认证校验兼容内存私钥
- `ssh_mcp/clients/paramiko_client.py` — 新增 `_load_pkey_from_memory()` 辅助函数；连接时优先用内存私钥 `pkey=`
- `ssh_mcp/session_manager.py` — 连接时优先用内存私钥
- `README.md` — 工具表 9→12 个，新增生产加固四项章节
- `VERSION` / `pyproject.toml` / `ssh_mcp/__init__.py` / `package.json` — 版本号 2.0.2 → 2.1.0

### 使用示例

```bash
# 生产跳板机 systemd unit
[Service]
User=sshlicco
Environment=SSH_RUNTIME_GUARD=true
Environment=SSH_SECRET_PROVIDER_ENABLED=true
Environment=SSH_SECRET_PROVIDER=command
Environment=SSH_SECRET_COMMAND_PROD_DB=vault kv get -field=private_key secret/ssh/prod-db
Environment=SSH_REMOTE_GUARD=true
Environment=SSH_APPROVAL_GATE=true
Environment=SSH_AUDIT_LOG_PATH=/var/log/ssh-licco/audit.log
```

```python
# AI 高危命令审批工作流
# 1. 直接执行被拦截
ssh_execute(command="rm -rf /tmp/old_logs")  # → 审批门禁拦截

# 2. 申请审批
ssh_request_approval(command="rm -rf /tmp/old_logs", reason="清理过期日志")
# → approval_id=eb4c261d...

# 3. 运维人员审批
ssh_approve_command(approval_id="eb4c261d...", decision="approved", reviewer="ops-admin")

# 4. 携带 approval_id 执行（一次性消费）
ssh_execute(command="rm -rf /tmp/old_logs", approval_id="eb4c261d...")
```

### 验收

- `python test_hardening.py` 四项加固端到端测试全部通过（4/4）
- 既有测试套件 327 passed / 10 failed（10 个失败为既有环境问题，非本次引入，已 git stash 对比验证）

---

## [2.0.2] - 2026-06-23

### 修复

- 版本号同步与发布流程稳定化

---

## [1.9.0] - 2026-06-28

### 新增功能

- **多层安全确认机制**：危险操作默认被阻止，需要多层确认才能执行
  - 自动风险评估：SAFE/LOW/MEDIUM/HIGH/CRITICAL 五个风险级别
  - 分层确认：严重风险3次确认，高风险2次确认，中等风险1次确认
  - 默认阻止：危险命令（如 `rm -rf`）必须先确认，否则被阻止
  - 详细警告消息：显示风险级别、确认进度和操作提示

### 安全增强

- **风险评估系统**：新增 `RiskLevel` 枚举，自动识别命令风险
- **多层确认流程**：`confirm_dangerous=true` + `confirmation_layer` 参数组合确认
- **配置文件支持**：`config/multi_layer_confirmation.example.json` 提供详细配置选项
- **日志记录**：记录所有确认尝试、成功确认和被阻止的命令

### 修改的文件

- `ssh_mcp/security.py` - 添加 `RiskLevel` 枚举和多层确认方法
- `ssh_mcp/server.py` - 集成多层确认逻辑
- `config/multi_layer_confirmation.example.json` - 新增配置文件

### 使用示例

```python
# 危险命令默认被阻止
ssh_execute(command="rm -rf /tmp/test_cache/*")
# 输出：❌ 操作已被安全机制阻止 + 详细警告信息

# 确认执行（需要3次确认）
ssh_execute(command="rm -rf /tmp/test_cache/*", confirm_dangerous=True, confirmation_layer=1)
ssh_execute(command="rm -rf /tmp/test_cache/*", confirm_dangerous=True, confirmation_layer=2)
ssh_execute(command="rm -rf /tmp/test_cache/*", confirm_dangerous=True, confirmation_layer=3)
```

---

## [1.8.0] - 2026-06-28

### 修复

- 修复 session 管理和重连机制问题
- 升级版本到 v1.8.0 并移除废弃的 CLI 测试文件

---

## [1.7.0] - 2026-06-28

### 重大变更

- **移除 CLI 接口**：完全移除命令行工具接口，专注于 MCP 工具集
  - 删除 `ssh_mcp/cli.py` - CLI 主入口
  - 删除 `ssh_mcp/fallback_executor.py` - CLI 回退执行器
  - 删除 `ssh-licco.js` - Node.js 包装脚本
  - 删除 `install.js` - 自动安装脚本
  - 删除 `package.json` - npm 包配置
  - 移除 `pyproject.toml` 中的 `[project.scripts]` 配置

### 安全增强

- **强制安全确认**：所有危险操作必须通过 MCP 工具的 `confirm_dangerous` 参数明确确认
- **移除旁路风险**：不再有 CLI 可以直接调用，所有操作都受安全机制保护
- **审计更完整**：所有操作都通过 MCP 层，有完整的审计日志

### 使用方式变更

| 配置项 | 之前 | 现在 |
|-------|------|------|
| MCP 命令 | `"command": "ssh-licco"` | `"command": "python -m ssh_mcp.server"` |
| npx 启动 | `npx ssh-licco` | ❌ 已移除 |

### 保留的核心功能

- ✅ 完整的 MCP 工具集（9 个工具）
- ✅ 多级安全策略（STRICT/BALANCED/RELAXED）
- ✅ 所有 SSH 功能（连接、执行、文件传输、Docker、screen/tmux 等）
- ✅ Python 包安装（`pip install ssh-licco`）

---

## [1.6.5] - 2026-06-28

### 修复

- `server.list_sessions` 和 `server._execute` 中 `session_info` 属性访问修复，改为 `session_info.config.username` / `session_info.config.host`，避免属性缺失导致崩溃
- `list_sessions` 输出中使用 `session._connected_at` / `session._last_activity` 并增加 `N/A` 兜底，防止 session 未完全初始化时崩溃

### 变更

- 版本号更新至 1.6.5

---

## [1.6.2] - 2026-06-28

### 修复

- `ConfigManager.__init__` 新增 `server_config_path` 参数，支持测试和外部调用方按需指定服务器配置文件路径
- `ssh_connect` 接受 MCP 客户端以字符串 `"22"` 形式传入的端口，自动强转为 `int`（MCP 协议下 JSON schema 声明 integer，但部分客户端仍按字符串发送）
- `ConfigManager.add_host` 增加 IP+端口重复校验，已存在相同 host:port 的主机时静默跳过，避免误添加
- 修复 `SessionManager.get_session` 在遇到已断开 session 时引用未初始化的 `self._logger` 导致 `AttributeError` 的问题（断连时自动清理逻辑此前会崩溃，掩盖真实的连接断开信号）

### 变更

- 测试用例 409 → 410（新增 `test_get_session_disconnected_auto_clean` 覆盖断连自动清理场景）

---

## [1.5.0] - 2026-06-20

### 新增

- 安全策略白名单配置文件支持：
  - 新增 `config/allowed_commands.example.json` 配置示例
  - `CommandValidator.from_config_file()` 类方法支持从 JSON 文件加载白名单
  - `create_validators_from_env()` 支持 `SSH_ALLOWED_COMMANDS_FILE` 环境变量
- 常用运维命令加入内置白名单：`nginx`、`systemctl`、`curl`、`apache2`、`httpd`、`caddy`、`haproxy`、`traefik`、`pm2`、`lscpu`、`lsblk`、`ip`、`snap` 等
- 后台任务日志状态细化为 5 种，并附诊断信息：
  - ✅ SUCCESS：命令执行成功（`EXIT=0`）
  - ❌ COMMAND_FAILED：命令执行失败（`EXIT>0`），附带退出码诊断
  - ⚠️ STATUS_ABNORMAL：进程异常终止（被信号杀死/OOM，未写入 exit 文件）
  - 🟢 RUNNING：后台任务仍在运行
  - 🔴 STARTUP_FAILED：任务启动失败（nohup/shell 错误），附带启动失败诊断

### 修复

- 修复 Windows 上 `PathValidator` 使用 `Path` 导致远程 Unix 路径验证失败的问题，改为 `PurePosixPath`
- 修复 `KeyManager.load_key` 不支持 OpenSSH 格式私钥的问题，优先尝试 `load_ssh_private_key`

### 变更

- 3 个原本跳过的测试现在全部通过
- 文档 `docs/CONTRIBUTING.md` 增加语义化版本 xyz 升级规则的详细说明

---

## [1.4.0] - 2026-06-20

### 新增

- `relaxed` 安全级别改为黑名单机制，仅拦截 `rm -rf /`、`mkfs`、`dd`、`fork bomb` 等高危命令
- `ssh_connect` 支持 `sudo_password` 参数，`ssh_execute` 支持 `use_sudo=True`
- `ssh_file_transfer` 新增 `remote_copy` direction，支持服务器间直传（`scp`/`rsync`）
- 后台任务元数据文件 `.meta`，便于 SSH 断开后跨 session 追踪

### 修复

- 修复后台任务"假失败"问题：DEAD 状态改为区分"已完成"和"已失败"
- 修复 `nginx -t`、`systemctl status` 等瞬时命令被误判为后台长任务的问题

---

## [1.3.3] - 2026-06-19

### 新增

- 后台任务可靠性增强：单次 SSH 调用 + `nohup bash -c` 包装，消除竞态
- 新增 `screen`/`tmux` 持久化会话支持（`session_type` 参数）
- 新增 `ssh_session` 和 `ssh_process` 工具

### 修复

- 保持 channel 引用，防止进程被 GC 回收
- `docker build` 不再被误判为后台任务

---

## [1.3.2] - 2026-06-19

### 修复

- 修复 `MCP_GITHUB_TOKEN` 配置
- 修复 Auto Release 工作流

---

## [1.2.1] - 2026-06-03

### 文档

- README 文档更新，同步到 PyPI

---

## [1.1.0] - 2026-06-01

### 变更

- 精简重构：MCP 工具从 15 个合并为 7 个
- 新增自动连接、智能后台检测、长任务等待

---

## [1.0.0] - 2026-05-31

### 新增

- 首个主要版本
- CLI 增强：`exec`、`upload`、`download`、`docker-build`、`list-hosts`
- 完整测试套件（402 用例）、看门狗监控、审计日志、连接池、批量执行

---

## [0.5.5] - 2026-05

### 优化

- 自动安装体系优化：依赖完整性检查、增量更新、Anaconda 检测、`cli.py` 精简

---

## [0.2.3] - 2026-03-14

### 修复

- 修复 `_logger` 初始化 bug

---

## [0.2.2] - 2026-03-14

### 安全

- 安全配置增强

---

## [0.2.1] - 2026-03-13

### 新增

- 多级安全策略
- 环境变量配置

---

## [0.2.0] - 2026-03-12

### 新增

- 安全验证模块
- 命令白名单

---

## [0.1.7] - 2026-03-11

### 新增

- 基础功能
- 后台任务
