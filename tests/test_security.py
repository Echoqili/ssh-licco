from __future__ import annotations

import os
from pathlib import PurePosixPath
from unittest.mock import patch

import pytest

from ssh_mcp.security import (
    CommandValidator,
    PathValidator,
    SecurityError,
    SecurityLevel,
    create_validators_from_env,
)


class TestSecurityLevel:
    def test_values(self):
        assert SecurityLevel.STRICT.value == "strict"
        assert SecurityLevel.BALANCED.value == "balanced"
        assert SecurityLevel.RELAXED.value == "relaxed"


class TestCommandValidator:
    def test_balanced_allows_simple_command(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        assert v.validate_command("ls") is True

    def test_balanced_allows_common_commands(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        for cmd in ["ls", "pwd", "cat file.txt", "grep pattern", "docker ps"]:
            assert v.validate_command(cmd) is True

    def test_balanced_blocks_pipe(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("ls | grep foo")

    def test_balanced_blocks_semicolon(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("ls ; rm -rf /")

    def test_balanced_blocks_command_substitution(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("echo $(whoami)")

    def test_balanced_blocks_backtick(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("echo `whoami`")

    def test_strict_blocks_redirect(self):
        v = CommandValidator(SecurityLevel.STRICT)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("echo hello > file.txt")

    def test_strict_blocks_ampersand(self):
        v = CommandValidator(SecurityLevel.STRICT)
        with pytest.raises(SecurityError, match="危险字符"):
            v.validate_command("ls 10 &")

    def test_relaxed_allows_pipe(self):
        v = CommandValidator(SecurityLevel.RELAXED)
        assert v.validate_command("ls | grep foo") is True

    def test_relaxed_allows_redirect(self):
        v = CommandValidator(SecurityLevel.RELAXED)
        assert v.validate_command("echo hello > file.txt") is True

    def test_empty_command(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="不能为空"):
            v.validate_command("")

    def test_whitespace_command(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="不能为空"):
            v.validate_command("   ")

    def test_unknown_command(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="不在允许列表中"):
            v.validate_command("evil_command arg1")

    def test_extra_allowed_commands(self):
        v = CommandValidator(SecurityLevel.BALANCED, extra_allowed_commands={"myapp"})
        assert v.validate_command("myapp --flag") is True

    def test_dangerous_keywords_passwd(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="受限关键字"):
            v.validate_command("cat /etc/passwd")

    def test_dangerous_keywords_shadow(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="受限关键字"):
            v.validate_command("cat /etc/shadow")

    def test_command_too_long(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        long_cmd = "ls " + "a" * 5000
        with pytest.raises(SecurityError, match="过长"):
            v.validate_command(long_cmd)

    def test_malformed_command(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="格式错误"):
            v.validate_command("echo 'unclosed")

    def test_docker_command_allowed(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        assert v.validate_command("docker build -t myapp .") is True

    def test_git_command_allowed(self):
        v = CommandValidator(SecurityLevel.BALANCED)
        assert v.validate_command("git status") is True


class TestPathValidator:
    def test_valid_path(self):
        v = PathValidator(SecurityLevel.BALANCED, base_dir="/home")
        result = v.validate_path("user/file.txt")
        assert str(result).startswith(str(v.base_dir))

    def test_path_traversal_attack(self):
        v = PathValidator(SecurityLevel.BALANCED, base_dir="/home")
        with pytest.raises(SecurityError, match="遍历"):
            v.validate_path("../../../etc/passwd")

    def test_empty_path(self):
        v = PathValidator(SecurityLevel.BALANCED)
        with pytest.raises(SecurityError, match="不能为空"):
            v.validate_path("")

    def test_forbidden_path_etc(self):
        """测试禁止访问 /etc/shadow（PurePosixPath 确保跨平台兼容）"""
        v = PathValidator(SecurityLevel.BALANCED, base_dir="/")
        with pytest.raises(SecurityError, match="敏感路径"):
            v.validate_path("etc/shadow")

    def test_forbidden_path_root(self):
        """测试禁止访问 /root/.ssh（PurePosixPath 确保跨平台兼容）"""
        v = PathValidator(SecurityLevel.BALANCED, base_dir="/")
        with pytest.raises(SecurityError, match="敏感路径"):
            v.validate_path("root/.ssh")

    def test_relaxed_no_forbidden_paths(self):
        v = PathValidator(SecurityLevel.RELAXED, base_dir="/")
        result = v.validate_path("etc/config")
        assert result is not None

    def test_strict_blocks_traversal(self):
        v = PathValidator(SecurityLevel.STRICT, base_dir="/home")
        with pytest.raises(SecurityError, match="遍历"):
            v.validate_path("../../tmp/evil")

    def test_extra_allowed_paths(self):
        v = PathValidator(SecurityLevel.BALANCED, base_dir="/home", extra_allowed_paths=["/data"])
        assert v.extra_allowed_paths == ["/data"]


class TestCreateValidatorsFromEnv:
    def test_default_balanced(self):
        with patch.dict(os.environ, {}, clear=True):
            cv, pv = create_validators_from_env()
            assert cv.security_level == SecurityLevel.BALANCED

    def test_strict_level(self):
        with patch.dict(os.environ, {"SSH_SECURITY_LEVEL": "strict"}):
            cv, pv = create_validators_from_env()
            assert cv.security_level == SecurityLevel.STRICT

    def test_relaxed_level(self):
        with patch.dict(os.environ, {"SSH_SECURITY_LEVEL": "relaxed"}):
            cv, pv = create_validators_from_env()
            assert cv.security_level == SecurityLevel.RELAXED

    def test_unknown_level_defaults_balanced(self):
        with patch.dict(os.environ, {"SSH_SECURITY_LEVEL": "unknown"}):
            cv, pv = create_validators_from_env()
            assert cv.security_level == SecurityLevel.BALANCED

    def test_extra_commands(self):
        with patch.dict(os.environ, {"SSH_EXTRA_ALLOWED_COMMANDS": "myapp,mytool"}):
            cv, pv = create_validators_from_env()
            assert "myapp" in cv.allowed_commands
            assert "mytool" in cv.allowed_commands

    def test_custom_base_dir(self):
        with patch.dict(os.environ, {"SSH_BASE_DIR": "/data"}):
            cv, pv = create_validators_from_env()
            assert "data" in str(pv.base_dir)
