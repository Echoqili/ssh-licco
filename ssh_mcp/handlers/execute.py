"""Handler for ssh_execute and background task execution."""

from __future__ import annotations

import asyncio
import os
import shlex
import uuid

from mcp.types import TextContent

from ..security import SecurityError, command_validator
from .connect import handle_connect
from .context import HandlerContext
from .utils import (
    diagnose_exit_code,
    diagnose_startup_failure,
    ensure_session,
    sanitize_remote_path,
    should_run_background,
)


async def handle_execute(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Handle ssh_execute, background tasks, execute-wait, and task-status."""
    command = args["command"]
    timeout = args.get("timeout", 120)  # 默认 120s，避免 docker pull/pg_basebackup 等长任务超时
    background = args.get("background", None)

    # Resolve session via session_id / name / host / env fallback
    session_id = await ensure_session(ctx, args, handle_connect)
    if not session_id:
        return [
            TextContent(
                type="text", text="No session_id, name, host, or SSH_HOST env var configured."
            )
        ]

    # Security validation with multi-layer confirmation
    # confirm_dangerous=True 时跳过安全检查（用户明确确认执行危险操作）
    confirm_dangerous = args.get("confirm_dangerous", False)
    confirmation_layer = args.get("confirmation_layer", 1)  # 当前确认层级

    # 多层安全确认检查
    can_execute, confirmation_message = command_validator.check_multi_layer_confirmation(
        command, confirm_dangerous, confirmation_layer
    )

    if not can_execute:
        ctx.logger.warning(f"Command blocked by multi-layer confirmation: {command}")
        return [
            TextContent(
                type="text",
                text=f"""❌ 操作已被安全机制阻止

{confirmation_message}

🛡️ 当前安全级别: {os.getenv("SSH_SECURITY_LEVEL", "balanced")}
🔍 风险评估: {command_validator.assess_risk_level(command).value}
📊 需要确认层级: {command_validator.get_required_confirmations(command)}

💡 提示：
- 对于危险操作，系统要求多层确认以确保安全
- 请仔细阅读警告信息，确保完全理解操作后果
- 如确需执行，请设置 confirm_dangerous=true 并增加 confirmation_layer 参数
""",
            )
        ]

    # 如果通过了多层确认，记录日志
    if confirmation_message:
        ctx.logger.info(f"Multi-layer confirmation passed: {confirmation_message}")

    # 硬拦截：与安全级别、confirm_dangerous、confirmation_layer 都无关，任何情况下都生效
    try:
        command_validator.check_hard_block(command)
    except SecurityError as e:
        ctx.logger.error(f"Command hard-blocked: {e}")
        return [
            TextContent(
                type="text",
                text=f"""❌ 命令被硬拦截，无法绕过

Command: {command}
Reason: {str(e)}

此操作属于灾难性命令（如 rm -rf 绝对路径、mkfs、dd 覆盘、fork-bomb 等），
任何安全级别、任何参数（包括 confirm_dangerous=true）都无法使其通过 MCP 执行。
如确需执行，请直接通过 SSH 登录服务器操作。

Current security level: {os.getenv("SSH_SECURITY_LEVEL", "balanced")}""",
            )
        ]

    # 原有的安全检查逻辑（保持兼容性）
    if not confirm_dangerous:
        try:
            command_validator.validate_command(command)
        except SecurityError as e:
            ctx.logger.error(f"Command blocked: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"""❌ 命令已被安全机制阻止

Command: {command}
Reason: {str(e)}

Solutions:
1. Set SSH_SECURITY_LEVEL=relaxed in MCP env config
2. Add SSH_EXTRA_ALLOWED_COMMANDS with the blocked command
3. Set confirm_dangerous=true in ssh_execute args to bypass (use with caution!)

Current security level: {os.getenv("SSH_SECURITY_LEVEL", "balanced")}""",
                )
            ]
    else:
        # 风险评估和日志记录
        risk_level, risk_desc = command_validator.get_risk_description(command)
        ctx.logger.warning(
            f"Dangerous command execution approved: {command} | "
            f"Risk: {risk_level.value} - {risk_desc}"
        )

    # Auto-detect background if not specified
    if background is None:
        background = should_run_background(command)

    if background:
        return await execute_background(ctx, session_id, command, args, timeout)

    # Normal execution
    session = await ctx.session_manager.get_session(session_id)
    if not session:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]

    # Sudo 包装：use_sudo=True 时用 sudo -S 执行，密码通过 stdin 传递
    # get_pty=True 分配伪终端，解决远端 sudoers 配置 requiretty 的问题
    stdin_data = None
    get_pty = False
    use_sudo = args.get("use_sudo", False)
    if use_sudo:
        sudo_pwd = getattr(session.config, "sudo_password", None)
        if not sudo_pwd:
            return [
                TextContent(
                    type="text",
                    text=(
                        "use_sudo=True but no sudo_password configured.\n"
                        "Please set sudo_password in ssh_connect or SSH_SUDO_PASSWORD env var."
                    ),
                )
            ]
        # sudo -S 从 stdin 读密码，-p '' 抑制提示符，bash -c 包装原始命令
        command = f"sudo -S -p '' bash -c {shlex.quote(command)}"
        stdin_data = sudo_pwd + "\n"
        get_pty = True

    result = await session.execute_command(
        command, timeout=timeout, stdin_data=stdin_data, get_pty=get_pty
    )

    if ctx.audit:
        session_info = await ctx.session_manager.get_session(session_id)
        ctx.audit.log_command(
            username=session_info.config.username if session_info else "unknown",
            host=session_info.config.host if session_info else "unknown",
            command=command,
            return_code=result.get("exit_code", -1),
            stdout_length=len(result.get("stdout", "")),
            stderr_length=len(result.get("stderr", "")),
            session_id=session_id,
            execution_time_ms=0,
        )

    # 统一输出格式：包含 session 标识，便于确认命令在哪个主机执行
    # 格式：Exit Code / Session / STDOUT / STDERR，各区块用 --- 分隔
    output = f"Exit Code: {result['exit_code']}\n"
    output += f"Session: {session_id} ({session.config.host}:{session.config.port})\n"
    if result["stdout"]:
        output += f"\n--- STDOUT ---\n{result['stdout']}"
    if result["stderr"]:
        output += f"\n--- STDERR ---\n{result['stderr']}"

    return [TextContent(type="text", text=output)]


async def execute_background(
    ctx: HandlerContext, session_id: str, command: str, args: dict, timeout: int
) -> list[TextContent]:
    """Execute a command as a background task with proper nohup + bash -c wrapping."""
    workdir = args.get("workdir", "/tmp")
    log_file = args.get("log_file", "/tmp/background_task.log")
    wait = args.get("wait", False)
    wait_timeout = args.get("wait_timeout", 60)
    session_type = args.get("session_type", "nohup")  # "nohup" | "screen" | "tmux"

    # Validate the base command
    try:
        command_validator.validate_command(command.split()[0] if command.split() else "")
    except SecurityError as e:
        return [TextContent(type="text", text=f"Security error: {str(e)}")]

    # workdir/log_file are remote paths, don't use local path_validator
    try:
        safe_workdir = sanitize_remote_path(workdir)
        safe_log_file = sanitize_remote_path(log_file)
    except SecurityError as e:
        return [TextContent(type="text", text=f"Path not allowed: {str(e)}")]

    # Block dangerous patterns
    dangerous_patterns = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){:|:&};:", "chmod -R 777 /"]
    for pattern in dangerous_patterns:
        if pattern in command:
            return [TextContent(type="text", text=f"Dangerous operation blocked: '{pattern}'")]

    task_id = str(uuid.uuid4())[:8]
    pid_file = f"/tmp/task_{task_id}.pid"
    # 元数据文件：记录命令、日志路径、工作目录，便于跨 session 追踪
    meta_file = f"/tmp/task_{task_id}.meta"

    # ── screen / tmux session support ──
    if session_type in ("screen", "tmux"):
        # 写入元数据（异步，不阻塞）
        meta_content = (
            f"command={command}\n"
            f"log_file={safe_log_file}\n"
            f"workdir={safe_workdir}\n"
            f"session_type={session_type}\n"
        )
        await ctx.session_manager.execute_command(
            session_id, f"echo {shlex.quote(meta_content)} > {shlex.quote(meta_file)}", timeout=5
        )
        return await execute_background_session(
            ctx,
            session_id,
            command,
            safe_workdir,
            safe_log_file,
            session_type,
            task_id,
            wait,
            wait_timeout,
        )

    # ── nohup mode (default): single SSH call, no race condition ──
    # Use shlex.quote() to safely escape the command and paths for bash -c.
    # The wrapper: 写元数据 → cd → nohup bash -c '...' → capture PID → sleep → check alive.
    # 内层命令结束后写入 exit_file，外层读取以区分"已完成"和"仍在运行"。
    exit_file = f"/tmp/task_{task_id}.exit"
    wrapped_command = f"{command}; echo $? > {shlex.quote(exit_file)}"
    meta_content = (
        f"command={command}\nlog_file={safe_log_file}\nworkdir={safe_workdir}\nsession_type=nohup\n"
    )
    check_cmd = (
        f"echo {shlex.quote(meta_content)} > {shlex.quote(meta_file)} && "
        f"cd {shlex.quote(safe_workdir)} && "
        f"nohup bash -c {shlex.quote(wrapped_command)} "
        f"> {shlex.quote(safe_log_file)} 2>&1 < /dev/null & "
        f"PID=$! && "
        f"echo $PID > {shlex.quote(pid_file)} && "
        f"sleep 1 && "
        f"if ps -p $PID > /dev/null 2>&1; then "
        f"echo 'PID='$PID' STATUS=RUNNING'; "
        f"else "
        f"EXIT=$(cat {shlex.quote(exit_file)} 2>/dev/null || echo -1); "
        f"echo 'PID='$PID' STATUS=COMPLETED EXIT='$EXIT; "
        f"echo '--- LOG ---'; "
        f"cat {shlex.quote(safe_log_file)} 2>/dev/null || echo '(no output)'; "
        f"fi"
    )

    try:
        # Execute as a single command (background=False) — the wrapper
        # includes sleep + status check, so it returns in ~1 second.
        result = await ctx.session_manager.execute_command(
            session_id, check_cmd, timeout=timeout + 5, background=False
        )
    except Exception as e:
        return [TextContent(type="text", text=f"Error starting background task: {str(e)}")]

    start_stdout = (result.get("stdout") or "").strip()
    start_stderr = (result.get("stderr") or "").strip()

    # Parse output: PID=xxx STATUS=RUNNING|COMPLETED EXIT=0
    pid = ""
    status = ""
    exit_code_str = ""
    log_tail = ""
    in_log = False
    for line in start_stdout.splitlines():
        if line.startswith("PID="):
            # 格式: PID=12345 STATUS=RUNNING  或  PID=12345 STATUS=COMPLETED EXIT=0
            for part in line.split():
                if part.startswith("PID="):
                    pid = part.split("=", 1)[1].strip()
                elif part.startswith("STATUS="):
                    status = part.split("=", 1)[1].strip()
                elif part.startswith("EXIT="):
                    exit_code_str = part.split("=", 1)[1].strip()
        elif line == "--- LOG ---":
            in_log = True
        elif in_log:
            log_tail += line + "\n"

    # ── 状态判定：区分 5 种情况 ──
    #
    # 1. ✅ SUCCESS         — STATUS=COMPLETED, EXIT=0   命令执行成功
    # 2. ❌ COMMAND_FAILED  — STATUS=COMPLETED, EXIT>0    命令执行失败（非零退出码）
    # 3. ⚠️ STATUS_ABNORMAL — STATUS=COMPLETED, EXIT=-1   进程异常终止（被信号/OOM杀，未写exit文件）
    # 4. 🟢 RUNNING         — STATUS=RUNNING              后台任务仍在运行
    # 5. 🔴 STARTUP_FAILED  — 无 PID 或无 STATUS          任务启动失败（nohup/shell 错误）

    # 情况 1-3：命令已执行完毕（有 STATUS=COMPLETED）
    if status == "COMPLETED":
        exit_code = int(exit_code_str) if exit_code_str.lstrip("-").isdigit() else -1

        # 统一头部信息：包含 session 标识，便于确认命令在哪个主机执行
        header = (
            f"Command: {command}\n"
            f"Session: {session_id}\n"
            f"PID: {pid}\n"
            f"Exit Code: {exit_code}\n"
            f"Working Directory: {safe_workdir}\n"
        )
        # LOG 说明：nohup 用 > log 2>&1 合并了 stdout 和 stderr
        log_section = f"--- LOG (stdout+stderr) ---\n{log_tail or '(no output)'}"

        if exit_code == 0:
            # ✅ 情况 1：命令执行成功
            return [
                TextContent(
                    type="text",
                    text=(f"✅ Background Task Completed Successfully!\n\n{header}{log_section}"),
                )
            ]

        elif exit_code > 0:
            # ❌ 情况 2：命令执行失败（非零退出码）
            # 常见原因：命令语法错误、文件不存在、权限不足、依赖缺失
            hint = diagnose_exit_code(exit_code, log_tail, start_stderr)
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Background Task Failed (exit code {exit_code})!\n\n"
                        f"{header}{hint}"
                        f"--- TASK START STDERR ---\n{start_stderr or '(none)'}\n"
                        f"{log_section}"
                    ),
                )
            ]

        else:
            # ⚠️ 情况 3：进程异常终止（exit_code == -1，未写入 exit 文件）
            # 常见原因：被 SIGKILL/SIGTERM 杀死、OOM Killer、段错误
            return [
                TextContent(
                    type="text",
                    text=(
                        f"⚠️ Background Task Terminated Abnormally!\n\n"
                        f"{header}"
                        f"\n可能原因：\n"
                        f"  - 被 SIGKILL/SIGTERM 信号终止（如 systemctl stop、kill -9）\n"
                        f"  - OOM Killer 杀死（内存不足，检查 dmesg | grep -i oom）\n"
                        f"  - 段错误/总线错误（程序 bug，检查 core dump）\n"
                        f"  - 父进程退出导致子进程被终止\n"
                        f"\n--- TASK START STDERR ---\n{start_stderr or '(none)'}\n"
                        f"{log_section}"
                    ),
                )
            ]

    # 🟢 情况 4：仍在运行
    if status == "RUNNING" and pid:
        if wait:
            output = await wait_for_task_completion(
                ctx=ctx,
                session_id=session_id,
                task_id=task_id,
                log_file=safe_log_file,
                timeout=wait_timeout,
            )
        else:
            output = f"""🟢 Background Task Started!

Task ID: {task_id}
PID: {pid}
Command: {command}
Working Directory: {safe_workdir}
Log File: {safe_log_file}

---
To check progress, use:
  ssh_execute(session_id="{session_id}", command="tail -f {safe_log_file}")
To view full log:
  ssh_execute(session_id="{session_id}", command="cat {safe_log_file}")
To check if still running:
  ssh_execute(session_id="{session_id}", command="ps -p {pid}")
After SSH reconnect, list all tasks:
  ssh_process(action="list", session_id="<new_session_id>")
  ssh_process(action="status", session_id="<new_session_id>", task_id="{task_id}")
"""
        return [TextContent(type="text", text=output)]

    # 🔴 情况 5：任务启动失败（无 PID 或无 STATUS）
    # 常见原因：工作目录不存在、bash 不可用、SSH 连接异常、权限拒绝
    startup_hint = diagnose_startup_failure(start_stdout, start_stderr, safe_workdir)
    return [
        TextContent(
            type="text",
            text=(
                f"🔴 Background Task Failed to Start!\n\n"
                f"Command: {command}\n"
                f"PID: {pid or '(none)'}\n"
                f"Working Directory: {safe_workdir}\n"
                f"{startup_hint}"
                f"--- STDOUT ---\n{start_stdout or '(none)'}\n"
                f"--- STDERR ---\n{start_stderr or '(none)'}\n"
                f"--- LOG TAIL ---\n{log_tail or '(no log output)'}"
            ),
        )
    ]


async def execute_background_session(
    ctx: HandlerContext,
    session_id: str,
    command: str,
    workdir: str,
    log_file: str,
    session_type: str,
    task_id: str,
    wait: bool,
    wait_timeout: int,
) -> list[TextContent]:
    """Execute a command inside a screen/tmux session for persistent long-running tasks."""
    session_name = f"ssh_mcp_{task_id}"
    escaped_cmd = command.replace("'", "'\\''")

    if session_type == "screen":
        # screen -dmS <name> bash -c 'cd <dir> && <cmd> > <log> 2>&1'
        launch_cmd = (
            f"screen -dmS {shlex.quote(session_name)} bash -c "
            f"'cd {shlex.quote(workdir)} && {escaped_cmd} > {shlex.quote(log_file)} 2>&1'"
        )
    else:  # tmux
        launch_cmd = (
            f"tmux new-session -d -s {shlex.quote(session_name)} "
            f"'cd {shlex.quote(workdir)} && {escaped_cmd} > {shlex.quote(log_file)} 2>&1'"
        )

    try:
        result = await ctx.session_manager.execute_command(
            session_id, launch_cmd, timeout=10, background=False
        )
    except Exception as e:
        return [TextContent(type="text", text=f"Error starting {session_type} session: {str(e)}")]

    stderr = (result.get("stderr") or "").strip()
    if stderr:
        return [
            TextContent(
                type="text",
                text=(
                    f"Failed to start {session_type} session!\n\n"
                    f"Session: {session_name}\n"
                    f"Command: {command}\n"
                    f"Error: {stderr}"
                ),
            )
        ]

    if wait:
        output = await wait_for_task_completion(
            ctx=ctx, session_id=session_id, task_id=task_id, log_file=log_file, timeout=wait_timeout
        )
    else:
        attach_cmd = (
            f"screen -r {session_name}"
            if session_type == "screen"
            else f"tmux attach -t {session_name}"
        )
        kill_cmd = (
            f"screen -XS {session_name} quit"
            if session_type == "screen"
            else f"tmux kill-session -t {session_name}"
        )
        output = f"""{session_type.upper()} Session Started!

Task ID: {task_id}
Session Name: {session_name}
Command: {command}
Working Directory: {workdir}
Log File: {log_file}

---
To attach to session:
  ssh_execute(session_id="{session_id}", command="{attach_cmd}")
To view log:
  ssh_execute(session_id="{session_id}", command="cat {log_file}")
To kill session:
  ssh_execute(session_id="{session_id}", command="{kill_cmd}")
"""

    return [TextContent(type="text", text=output)]


async def wait_for_task_completion(
    ctx: HandlerContext, session_id: str, task_id: str, log_file: str, timeout: int
) -> str:
    """Wait for a background task to complete and return its output."""
    pid_file = f"/tmp/task_{task_id}.pid"
    exit_file = f"/tmp/task_{task_id}.exit"
    elapsed = 0
    interval = 2

    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval

        check_cmd = (
            f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); "
            "if ps -p $PID > /dev/null 2>&1; then echo 'RUNNING'; "
            "else echo 'COMPLETED'; fi; else echo 'NOT_FOUND'; fi"
        )
        result = await ctx.session_manager.execute_command(session_id, check_cmd, timeout=10)
        status = result.get("stdout", "").strip()

        if status == "COMPLETED" or status == "NOT_FOUND":
            # 读取退出码
            exit_result = await ctx.session_manager.execute_command(
                session_id, f"cat {exit_file} 2>/dev/null || echo -1", timeout=10
            )
            exit_code_str = (exit_result.get("stdout") or "-1").strip()
            exit_code = int(exit_code_str) if exit_code_str.lstrip("-").isdigit() else -1

            log_cmd = (
                f"if [ -f {log_file} ]; then cat {log_file}; else echo 'No log file found'; fi"
            )
            log_result = await ctx.session_manager.execute_command(session_id, log_cmd, timeout=10)
            log_content = log_result.get("stdout", "")

            status_label = (
                "Completed Successfully" if exit_code == 0 else f"Failed (exit code {exit_code})"
            )
            return f"""Task {status_label}!

Task ID: {task_id}
Exit Code: {exit_code}
Execution Time: ~{elapsed} seconds
Log File: {log_file}

---
Command Output:
{log_content}
"""

    return f"""Task Still Running (Timeout)

Task ID: {task_id}
Waited: {elapsed} seconds (timeout: {timeout}s)
Log File: {log_file}

---
Use ssh_execute to check: cat {log_file}
"""
