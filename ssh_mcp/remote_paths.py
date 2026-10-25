"""Shared remote file access rules (independent of command security level)."""

import re
from pathlib import PurePosixPath, PureWindowsPath

# 远程 Unix/Linux 敏感路径黑名单
FORBIDDEN_REMOTE_PATHS = [
    "/etc",
    "/root",
    "/boot",
    "/proc",
    "/sys",
    "/dev",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/lib",
    "/lib64",
    "/var/lib/postgresql",
    "/var/lib/mysql",
    "/var/lib/redis",
    "/var/lib/docker",
    "/var/log",
    "/var/spool",
    "/var/mail",
    "/home/*/.ssh",
]

# 远程 Windows 敏感路径黑名单（支持大小写不敏感匹配）
FORBIDDEN_WINDOWS_PATHS = [
    r"C:\Windows",
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\inetpub",
    r"C:\Users\Default",
    r"C:\Users\Public",
    r"C:\Recovery",
    r"C:\System Volume Information",
    r"C:\$Recycle.Bin",
]


def _is_windows_path(path: str) -> bool:
    """根据路径特征判断是否为 Windows 风格路径。"""
    if re.match(r"^[A-Za-z]:\\", path):
        return True
    if path.startswith("\\\\"):
        return True
    # 仅包含反斜杠且不含正斜杠时，视为 Windows 路径
    if "\\" in path and "/" not in path:
        return True
    return False


def _validate_remote_path(remote_path: str, operation: str = "access") -> tuple[bool, str]:
    """校验远程路径是否安全，自动识别 Windows / Unix 路径风格。

    Returns:
        (is_safe, error_message)
    """
    if not remote_path or not remote_path.strip():
        return False, "远程路径不能为空"

    if "\x00" in remote_path or remote_path != remote_path.strip():
        return False, "Invalid remote path"
    remote_path = remote_path.strip()

    if _is_windows_path(remote_path):
        # Windows 路径处理
        normalized = str(PureWindowsPath(remote_path))
        if ".." in normalized.split("\\"):
            return False, f"Windows 路径遍历被阻止：{remote_path}"

        if ".ssh" in [part.lower() for part in PureWindowsPath(normalized).parts]:
            return False, "SSH credential paths are protected"
        upper_normalized = normalized.upper()
        for forbidden in FORBIDDEN_WINDOWS_PATHS:
            upper_forbidden = forbidden.upper().rstrip("\\")
            if upper_normalized == upper_forbidden or upper_normalized.startswith(
                upper_forbidden + "\\"
            ):
                return False, f"禁止{operation} Windows 敏感路径：{forbidden}"

        return True, ""

    # Unix/Linux 路径处理
    normalized = str(PurePosixPath(remote_path)).rstrip("/") or "/"
    if ".." in normalized.split("/"):
        return False, f"路径遍历被阻止：{remote_path}"

    if normalized == "/" or ".ssh" in PurePosixPath(normalized).parts:
        return False, "Root and SSH credential paths are protected"
    path_for_check = normalized.rstrip("/*") or "/"
    for forbidden in FORBIDDEN_REMOTE_PATHS:
        if forbidden.endswith("/*"):
            prefix = forbidden[:-1]
            if path_for_check.startswith(prefix) or path_for_check + "/" == prefix:
                return False, f"禁止{operation}敏感路径：{forbidden}"
        elif path_for_check == forbidden or path_for_check.startswith(forbidden + "/"):
            return False, f"禁止{operation}敏感路径：{forbidden}"

    return True, ""
