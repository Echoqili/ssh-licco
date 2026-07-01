"""SSH-LICCO 运行时守护 — 加固点 1：运行账号最小权限

生产跳板机部署 ssh-licco 时，必须以专用普通运维账号启动，禁止 root / 禁止 sudo。
本模块在进程入口（run_server）处强制校验运行身份，发现违规立即拒绝启动。

启用方式（环境变量）：
    SSH_RUNTIME_GUARD=true            # 总开关，默认 false（开发/测试不强制）
    SSH_RUNTIME_ALLOW_ROOT=false      # 是否允许 root 启动，默认 false
    SSH_RUNTIME_ALLOWED_USERS=        # 逗号分隔的允许账号白名单，留空表示不限制具体用户名
                                       例如：sshlicco,ops
    SSH_RUNTIME_BLOCK_SUDO=true       # 检测 SUDO_* / PKEXEC_* 等提权环境变量，默认 true

为什么这样设计：
    - 跳板机是 SSH 代理的唯一执行点，进程权限 = 可下发的最大远端命令权限上限。
    - root / sudo 启动会让命令白名单形同虚设：任何白名单内的命令都能以 root 身份
      在跳板机本地造成破坏（例如读取本地私钥、改 hosts.json、注入 sudo_password）。
    - 因此"运行账号最小权限"是其它三项加固（密钥不落地、双层拦截、审批）的前置条件。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


class RuntimeGuardError(RuntimeError):
    """运行身份校验失败"""


@dataclass
class RuntimeCheckResult:
    ok: bool
    reason: str
    current_user: str
    is_root: bool
    is_sudo_context: bool


def _posix_user_name(uid: int) -> str:
    try:
        import pwd  # 仅 POSIX 可用

        return pwd.getpwuid(uid).pw_name
    except Exception:
        return str(uid)


def _current_user_name() -> str:
    """获取当前运行账号名。Windows 下返回 USERNAME 环境变量（仅用于提示，不强制）。"""
    if os.name == "posix":
        try:
            return _posix_user_name(os.getuid())
        except Exception:
            return os.getenv("USER", "unknown")
    # Windows 不强制（生产跳板机本身是 Linux），仅用于日志提示
    return os.getenv("USERNAME") or os.getenv("USER") or "unknown-windows-user"


def _is_root() -> bool:
    if os.name != "posix":
        return False
    return os.geteuid() == 0


def _is_sudo_context() -> bool:
    """检测 sudo / doas / pkexec 提权环境。"""
    sudo_markers = (
        "SUDO_USER",
        "SUDO_UID",
        "SUDO_GID",
        "SUDO_COMMAND",
        "PKEXEC_UID",
        "DOAS_USER",
    )
    return any(os.getenv(m) for m in sudo_markers)


def check_runtime_identity() -> RuntimeCheckResult:
    """执行运行账号最小权限校验。返回检查结果，不抛异常。"""
    current_user = _current_user_name()
    is_root = _is_root()
    is_sudo = _is_sudo_context()

    # POSIX 之外（Windows 开发环境）直接放行，生产跳板机本身是 Linux
    if os.name != "posix":
        return RuntimeCheckResult(
            ok=True,
            reason=f"non-POSIX platform ({os.name}), runtime guard skipped (dev only)",
            current_user=current_user,
            is_root=is_root,
            is_sudo_context=is_sudo,
        )

    allow_root = os.getenv("SSH_RUNTIME_ALLOW_ROOT", "false").lower() == "true"
    block_sudo = os.getenv("SSH_RUNTIME_BLOCK_SUDO", "true").lower() == "true"
    allowed_users_raw = os.getenv("SSH_RUNTIME_ALLOWED_USERS", "").strip()
    allowed_users = {u.strip() for u in allowed_users_raw.split(",") if u.strip()}

    # 1. root 拦截
    if is_root and not allow_root:
        return RuntimeCheckResult(
            ok=False,
            reason=(
                "ssh-licco 进程以 root 身份启动被拒绝。\n"
                "  生产跳板机必须使用专用普通运维账号运行，禁止 root 启动。\n"
                "  排查：检查 systemd unit 的 User= / 启动脚本的 su/sudo。\n"
                "  如确实需要在 root 下临时调试，设置 SSH_RUNTIME_ALLOW_ROOT=true（不推荐）。"
            ),
            current_user=current_user,
            is_root=is_root,
            is_sudo_context=is_sudo,
        )

    # 2. sudo 上下文拦截
    if is_sudo and block_sudo:
        return RuntimeCheckResult(
            ok=False,
            reason=(
                "ssh-licco 进程在 sudo/doas/pkexec 提权上下文中启动被拒绝。\n"
                "  生产跳板机禁止通过 sudo 启动 ssh-licco，请直接以专用账号登录后启动。\n"
                "  如需临时调试，设置 SSH_RUNTIME_BLOCK_SUDO=false（不推荐）。"
            ),
            current_user=current_user,
            is_root=is_root,
            is_sudo_context=is_sudo,
        )

    # 3. 用户白名单
    if allowed_users and current_user not in allowed_users:
        return RuntimeCheckResult(
            ok=False,
            reason=(
                f"ssh-licco 进程以账号 '{current_user}' 启动，不在白名单 {sorted(allowed_users)} 中。\n"
                "  请使用 SSH_RUNTIME_ALLOWED_USERS 中声明的专用运维账号启动。"
            ),
            current_user=current_user,
            is_root=is_root,
            is_sudo_context=is_sudo,
        )

    return RuntimeCheckResult(
        ok=True,
        reason="runtime identity OK",
        current_user=current_user,
        is_root=is_root,
        is_sudo_context=is_sudo,
    )


def enforce_runtime_guard() -> None:
    """入口处调用：开启守护时若校验失败，打印原因并 sys.exit(2)。

    未开启守护（SSH_RUNTIME_GUARD 未设为 true）时仅打印提示，不强制。
    """
    enabled = os.getenv("SSH_RUNTIME_GUARD", "false").lower() == "true"
    result = check_runtime_identity()

    if result.ok:
        # 即使通过，也把运行账号落到日志，便于审计
        print(
            f"[runtime_guard] identity check passed: user={result.current_user} "
            f"root={result.is_root} sudo_ctx={result.is_sudo_context}",
            file=sys.stderr,
        )
        return

    # 校验失败
    if enabled:
        print(f"[runtime_guard] FATAL: {result.reason}", file=sys.stderr)
        sys.exit(2)
    else:
        # 未开启守护，仅警告（开发/测试环境）
        print(
            f"[runtime_guard] WARNING (not enforced, set SSH_RUNTIME_GUARD=true to enforce): "
            f"{result.reason}",
            file=sys.stderr,
        )
