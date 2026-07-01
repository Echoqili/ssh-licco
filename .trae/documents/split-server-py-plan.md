# 拆分 ssh\_mcp/server.py 重构计划

## 背景与目标

`ssh_mcp/server.py` 当前约 2200 行，集中了 12 个 MCP 工具的 schema 定义、调度分发和具体实现。随着功能增加，单文件维护成本高、冲突概率大、单测定位困难。

本计划将其拆分为 `handlers/` 包：

* 每个工具（或相关工具组）一个模块

* schema 单独维护

* 共享状态通过上下文对象传递

* **保持现有测试不中断**：`tests/test_server.py` 大量调用 `server._handle_*()`，重构期间保留薄包装方法

## 当前现状

* `server.py` 中 `SSHMCPServer` 类包含：

  * `Tunnel` 辅助类

  * 环境配置加载、速率限制

  * `_setup_handlers()`：12 个 `Tool(...)` schema 内联定义 + MCP 调度

  * 12 个 `_handle_*` 私有方法

* 共享状态：`session_manager`、`key_manager`、`config_manager`、`_env_config`、`_logger`、`_audit`、`_tunnels`

* 共享辅助：`_ensure_session`、路径/命令处理、后台执行诊断等

## 目标目录结构

```
ssh_mcp/
├── __init__.py
├── server.py                  # 精简：初始化、速率限制、MCP 注册、_handle_* 薄包装
├── tunnel.py                  # Tunnel 类抽出（可选）
└── handlers/
    ├── __init__.py            # HANDLERS 注册表
    ├── base.py                # HandlerProtocol / 可选基类
    ├── context.py             # HandlerContext 共享状态容器
    ├── schemas.py             # 12 个 Tool 定义
    ├── utils.py               # _ensure_session、路径处理、诊断等共享辅助
    ├── connect.py             # ssh_connect、ssh_disconnect
    ├── execute.py             # ssh_execute（含 background、sudo、审批、remote_guard）
    ├── file_transfer.py       # ssh_file_transfer
    ├── host.py                # ssh_host
    ├── docker.py              # ssh_docker
    ├── key.py                 # ssh_generate_key
    ├── session.py             # ssh_session (screen/tmux)
    ├── process.py             # ssh_process + tunnel_open/close/list
    └── approval.py            # ssh_request_approval、ssh_approve_command、ssh_list_approvals
```

## 关键设计决策

### 1. 共享状态传递：上下文对象

新增 `handlers/context.py`：

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class HandlerContext:
    session_manager: Any
    key_manager: Any
    config_manager: Any
    env_config: dict
    logger: Any
    audit: Any | None
    tunnels: dict[int, "Tunnel"]
```

`SSHMCPServer.__init__` 中实例化 `self._ctx`，所有 handler 函数签名统一为：

```python
async def handle_xxx(ctx: HandlerContext, args: dict) -> list[TextContent]
```

速率限制保留在 server 层，调用 handler 前统一检查。

### 2. Schema 与 handler 解耦

* `handlers/schemas.py` 定义 `TOOLS: dict[str, Tool]`

* `server.py` 的 `list_tools()` 返回 `list(schemas.TOOLS.values())`

* `handlers/__init__.py` 维护 `HANDLERS: dict[str, Callable]` 注册表

* `server.py` 的 `call_tool()` 改为注册表查找，不再使用长 if/elif 链

### 3. 测试兼容：保留 `_handle_*` 薄包装

重构期间 `server.py` 保留：

```python
async def _handle_connect(self, args: dict) -> list[TextContent]:
    return await connect.handle_connect(self._ctx, args)
```

这样 `tests/test_server.py` 无需修改即可通过。后续可决定是否移除。

### 4. 共享辅助归属

| 原方法/类                                                                           | 归属                                 |
| ------------------------------------------------------------------------------- | ---------------------------------- |
| `_load_env_config`                                                              | 保留 server.py（仅初始化）                 |
| `_check_rate_limit`                                                             | 保留 server.py（调度前检查）                |
| `_ensure_session`                                                               | `handlers/utils.py`                |
| `_sanitize_remote_path`、`_shell_quote`                                          | `handlers/utils.py`                |
| `_diagnose_exit_code`、`_diagnose_startup_failure`、`_should_run_background`      | `handlers/utils.py` 或 `execute.py` |
| `_execute_background`、`_execute_background_session`、`_wait_for_task_completion` | `handlers/execute.py`              |
| `Tunnel` 类                                                                      | `ssh_mcp/tunnel.py`                |

## 分阶段实施步骤

### Phase 0：搭建骨架

1. 创建 `ssh_mcp/handlers/` 包
2. 新增 `handlers/context.py`、`handlers/base.py`
3. 新增 `handlers/schemas.py`，原样拷贝 12 个 schema
4. 新增 `ssh_mcp/tunnel.py`（复制 Tunnel 类，server.py 暂不删除原类）
5. 新增 `handlers/__init__.py` 导出 schemas 与后续 HANDLERS

**验收**：导入不报错，测试全部通过。

### Phase 1：Schema 迁移

1. `server.py` 的 `_setup_handlers()` 中 `list_tools()` 改为返回 `list(schemas.TOOLS.values())`
2. 删除 `server.py` 中 12 个内联 schema 定义

**验收**：`pytest tests/test_server.py` 通过。

### Phase 2：公共工具函数迁移

1. 将路径/命令处理、诊断函数迁移到 `handlers/utils.py`
2. `server.py` 中保留同名方法，内部委托给 `handlers/utils.py`

**验收**：测试继续通过。

### Phase 3：逐个迁移 handler

按依赖从少到多顺序：

1. `key.py`（ssh\_generate\_key）
2. `approval.py`（三个审批工具）
3. `host.py`（ssh\_host）
4. `connect.py`（ssh\_connect、ssh\_disconnect）
5. `file_transfer.py`
6. `session.py`
7. `execute.py`（最大，含 background 逻辑）
8. `docker.py`（依赖 execute background）
9. `process.py`（依赖 tunnels、execute background）

每完成一个模块，就将 `server.py` 中对应 `_handle_*` 改为委托，并运行测试。

**验收**：每阶段 `pytest tests/test_server.py` 全绿。

### Phase 4：Dispatch 重构

1. 在 `handlers/__init__.py` 建立完整 `HANDLERS` 注册表
2. `server.py` 的 `call_tool()` 改为：

```python
handler = HANDLERS.get(name)
if handler is None:
    return [TextContent(type="text", text=f"Unknown tool: {name}")]
return await handler(self._ctx, arguments)
```

**验收**：测试通过，可用真实 MCP client 做端到端抽查。

### Phase 5：清理（可选，稳定后再做）

* 删除 `server.py` 中 `_handle_*` 薄包装

* 更新测试直接导入 `handlers.*.handle_*`

* 删除 server.py 底部对 utils 的委托方法

* 删除 server.py 中旧 Tunnel 类（已迁移到 tunnel.py）

## 风险与缓解

| 风险                                          | 缓解                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------ |
| 测试直接依赖 `_handle_*`                          | 重构期间保留薄包装                                                          |
| `_ensure_session` 解析 `_handle_connect` 返回文本 | 保持现有调用路径，后续再提取 session\_id 返回函数                                    |
| `docker.py`/`process.py` 共享后台执行逻辑           | 后台逻辑放在 `execute.py`，其他模块显式导入                                       |
| `Tunnel` 可变状态共享                             | `HandlerContext.tunnels` 传递同一字典引用                                  |
| 循环导入                                        | `context.py` 不导入 handler；server.py 最后导入 handlers；utils 仅使用标准库/已有模块 |
| schema 拷贝遗漏                                 | diff 比对；加载后做 snapshot 测试                                           |

## 验证方式

1. 每阶段运行 `pytest tests/test_server.py -v`
2. 全阶段运行 `pytest tests/ -q`（目标 337 passed）
3. 启动服务并抽查关键工具：

   * `ssh_generate_key`

   * `ssh_host`（list/add/remove）

   * `ssh_request_approval` / `ssh_approve_command` / `ssh_list_approvals`

## 相关文件

* `d:\Pycharm_workplace\ssh-mcp\ssh_mcp\server.py`

* `d:\Pycharm_workplace\ssh-mcp\tests\test_server.py`

* 将新增：`ssh_mcp/handlers/context.py`、`schemas.py`、`utils.py`、`__init__.py`、各 handler 模块、`ssh_mcp/tunnel.py`

