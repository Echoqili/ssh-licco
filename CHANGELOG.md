# Changelog

本文件记录 SSH LICCO 项目的所有重要变更，遵循 [语义化版本规范](https://semver.org/lang/zh-CN/)。

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
