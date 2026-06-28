# Changelog

本文件记录 SSH LICCO 项目的所有重要变更，遵循 [语义化版本规范](https://semver.org/lang/zh-CN/)。

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
