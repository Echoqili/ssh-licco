"""Tests for ssh_mcp.security — Hard Block on Catastrophic Commands.

Spec: openspec/changes/hardblock-dangerous-commands/specs/ssh-security/spec.md
"""

from __future__ import annotations

import logging
import re

import pytest

from ssh_mcp.security import CommandValidator, SecurityError, SecurityLevel

# ---------------------------------------------------------------------------
# Parametrize fixtures
# ---------------------------------------------------------------------------

ABSOLUTE_PATH_RM_RF = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf /etc",
    "rm -rf /var/lib/postgresql/data",
    "rm -rf /home/user/junk/*",
    "rm -fr /etc",  # -fr variant
]

DISK_DESTRUCTIVE = [
    "mkfs.ext4 /dev/sda1",
    "mkfs.xfs /dev/nvme0n1",
    "dd if=/dev/zero of=/dev/sda bs=1M",
    "dd if=/dev/urandom of=/dev/nvme0n1",
    "chmod -R 777 /",
    "chmod -R 000 /",
    ":(){:|:&};:",
    ": ( ) { : | : & } ;",  # whitespace variant
    "echo junk > /dev/sda",
    "echo junk > /dev/nvme0n1",
    "echo junk >> /dev/sdb",
]

SAFE_DELETE = [
    "rm /tmp/test.log",
    "rm -f /var/log/app.log",  # -f without -r is still safe
    "rmdir /tmp/empty_dir",
]

ALL_LEVELS = [
    SecurityLevel.STRICT,
    SecurityLevel.BALANCED,
    SecurityLevel.RELAXED,
]


# ---------------------------------------------------------------------------
# 4.2: rm -rf on absolute paths is rejected in all security levels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", ABSOLUTE_PATH_RM_RF)
@pytest.mark.parametrize("level", ALL_LEVELS)
def test_hard_block_rejects_absolute_path_rm_rf(cmd: str, level: SecurityLevel) -> None:
    """rm -rf against any absolute path is hard-blocked regardless of security level."""
    v = CommandValidator(security_level=level)
    with pytest.raises(SecurityError) as exc_info:
        v.check_hard_block(cmd)
    assert exc_info.value.hard_block is True


@pytest.mark.parametrize("cmd", ABSOLUTE_PATH_RM_RF)
@pytest.mark.parametrize("level", ALL_LEVELS)
def test_hard_block_rejects_even_with_validate_command(cmd: str, level: SecurityLevel) -> None:
    """validate_command also runs the hard block first (so it works via the unified path)."""
    v = CommandValidator(security_level=level)
    with pytest.raises(SecurityError) as exc_info:
        v.validate_command(cmd)
    assert exc_info.value.hard_block is True


# ---------------------------------------------------------------------------
# 4.3: disk-destructive commands are rejected in all security levels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", DISK_DESTRUCTIVE)
@pytest.mark.parametrize("level", ALL_LEVELS)
def test_hard_block_rejects_disk_destructive(cmd: str, level: SecurityLevel) -> None:
    """mkfs / raw-disk dd / root chmod 777 / fork-bomb / raw redirect — all rejected."""
    v = CommandValidator(security_level=level)
    with pytest.raises(SecurityError) as exc_info:
        v.check_hard_block(cmd)
    assert exc_info.value.hard_block is True


# ---------------------------------------------------------------------------
# 4.4: safe delete operations still work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", SAFE_DELETE)
@pytest.mark.parametrize("level", ALL_LEVELS)
def test_safe_delete_still_allowed(cmd: str, level: SecurityLevel) -> None:
    """rm /tmp/file, rmdir empty, and rm -f single file must NOT be hard-blocked."""
    v = CommandValidator(security_level=level)
    # check_hard_block is the only thing we're testing here; should not raise.
    v.check_hard_block(cmd)


# ---------------------------------------------------------------------------
# 4.5: relative-path rm -rf is NOT hard-blocked (regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", [
    "rm -rf ./build/",
    "rm -rf relative/dir",
    "rm -rf ../sibling",
    "rm -rf .",
])
def test_soft_risk_relative_path_not_hard_blocked(cmd: str) -> None:
    """Relative-path rm -rf must not be hard-blocked (only absolute paths are)."""
    v = CommandValidator(security_level=SecurityLevel.BALANCED)
    # check_hard_block should pass (no exception)
    v.check_hard_block(cmd)


# ---------------------------------------------------------------------------
# 4.6: WARNING log is emitted on hard block, regex is not echoed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", ABSOLUTE_PATH_RM_RF[:2])
def test_hard_block_logs_warning_with_category(
    cmd: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A WARNING log line is emitted; it contains the category but not the regex."""
    v = CommandValidator(security_level=SecurityLevel.BALANCED)
    with caplog.at_level(logging.WARNING, logger="ssh_mcp.security"):
        with pytest.raises(SecurityError):
            v.check_hard_block(cmd)

    # At least one WARNING record exists
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings, f"no WARNING log emitted for {cmd}"

    # The category is in the log, the command is in the log
    joined = " ".join(r.getMessage() for r in warnings)
    assert cmd in joined, f"command not in log: {joined}"
    assert "category=" in joined, f"category label not in log: {joined}"

    # The log message must NOT contain raw regex syntax markers from the blacklist
    # (i.e. \s, \., \[, etc.) — only the human-readable category is allowed.
    for record in warnings:
        msg = record.getMessage()
        assert not re.search(r"\\[sdw+\[\]]", msg), (
            f"regex metacharacters leaked into log message: {msg}"
        )


def test_hard_block_message_does_not_mention_override() -> None:
    """The error message must not suggest any parameter can bypass the hard block."""
    v = CommandValidator(security_level=SecurityLevel.RELAXED)
    with pytest.raises(SecurityError) as exc_info:
        v.check_hard_block("rm -rf /etc")
    msg = str(exc_info.value)
    assert "confirm_dangerous" not in msg
    assert "confirmation_layer" not in msg
    assert "无法通过任何参数绕过" in msg or "无法绕过" in msg or "无法" in msg


# ---------------------------------------------------------------------------
# SecurityError attribute contract
# ---------------------------------------------------------------------------


def test_security_error_has_hard_block_attribute() -> None:
    """SecurityError exposes `hard_block: bool`; default is False, hard block sets True."""
    # Default (other errors)
    err = SecurityError("plain")
    assert err.hard_block is False

    # Hard block path
    v = CommandValidator(security_level=SecurityLevel.BALANCED)
    with pytest.raises(SecurityError) as exc_info:
        v.check_hard_block("rm -rf /")
    assert exc_info.value.hard_block is True


# ---------------------------------------------------------------------------
# Pattern coverage: every documented catastrophic pattern has a regex entry
# ---------------------------------------------------------------------------


def test_hard_block_patterns_cover_documented_categories() -> None:
    """The HARD_BLOCKED_PATTERNS set must include all categories in the spec."""
    expected_categories = {
        "absolute_path_rm_rf",
        "disk_format",
        "raw_disk_dd",
        "fork_bomb",
        "root_chmod",
        "raw_disk_redirect",
    }
    actual = {category for _, category in CommandValidator.HARD_BLOCKED_PATTERNS}
    assert expected_categories.issubset(actual), (
        f"missing categories: {expected_categories - actual}"
    )


# -----------------------------------------------------------------------------
# Deletion command parsing and backup generation
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("cmd,expected_targets", [
    ("rm -rf ./data", ["./data"]),
    ("rm -r ./data", ["./data"]),
    ("rm -fr ./data ./logs", ["./data", "./logs"]),
    ("rm --recursive --force ./data", ["./data"]),
    ("sudo rm -rf /home/user/tmp", ["/home/user/tmp"]),
    ("rm -rf -- ./data", ["./data"]),
    ("rm /tmp/single.log", ["/tmp/single.log"]),
    ("rm -f /tmp/single.log", ["/tmp/single.log"]),
    ("rmdir /tmp/empty_dir", ["/tmp/empty_dir"]),
    ("sudo rmdir /tmp/empty_dir", ["/tmp/empty_dir"]),
])
def test_parse_deletion_command_detects_deletion(cmd: str, expected_targets: list[str]) -> None:
    """普通 rm / rmdir / 递归 rm 都应被识别为需要备份确认的删除操作。"""
    from ssh_mcp.security import parse_deletion_command
    is_deletion, targets = parse_deletion_command(cmd)
    assert is_deletion is True
    assert targets == expected_targets


@pytest.mark.parametrize("cmd", [
    "rm",
    "rm --help",
    "rm --version",
    "rmdir",
    "cp -r ./a ./b",
    "echo hello",
])
def test_parse_deletion_command_ignores_non_deletion_commands(cmd: str) -> None:
    """无目标、帮助/版本或无关命令不应触发备份确认。"""
    from ssh_mcp.security import parse_deletion_command
    is_deletion, targets = parse_deletion_command(cmd)
    assert is_deletion is False
    assert targets == []


def test_generate_backup_command_quotes_targets() -> None:
    """备份命令应正确引用目标路径并包含时间戳目录。"""
    from ssh_mcp.security import generate_backup_command
    cmd = generate_backup_command(["./data", "./my logs"])
    assert cmd.startswith("mkdir -p /tmp/ssh_mcp_backup_")
    # shlex.quote 只在需要时加引号；重点是含空格的路径必须被引用
    assert "cp -a ./data './my logs'" in cmd
    assert "echo 'Backed up to /tmp/ssh_mcp_backup_" in cmd


def test_generate_backup_command_returns_empty_for_invalid_targets() -> None:
    """目标均为无效值时应返回空字符串。"""
    from ssh_mcp.security import generate_backup_command
    assert generate_backup_command(["", ".", ".."]) == ""


def test_format_backup_prompt_mentions_backup_before_delete() -> None:
    """提示文案应明确告知用户 backup_before_delete 参数。"""
    from ssh_mcp.security import format_backup_prompt
    prompt = format_backup_prompt("rm -rf ./data", ["./data"])
    assert "backup_before_delete=true" in prompt
    assert "backup_before_delete=false" in prompt
    assert "./data" in prompt
