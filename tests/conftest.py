from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Windows 下 os.environ 可能包含超长变量（如 ACC_PRODUCT_CONFIG_V3 > 32767 字符），
# 任何 patch.dict(os.environ, ...) 在退出恢复时都会逐个 os.environ[k]=v 触发
# _putenv 的 32767 限制抛 ValueError，污染后续测试（Path.home() 失败等）。
# 本 autouse fixture 在每个测试前把超长变量暂存移除，测试后恢复，隔离该环境问题。
_WIN_ENV_LEN_LIMIT = 32000


@pytest.fixture(autouse=True)
def _strip_oversized_env_vars():
    oversized = {}
    for k in list(os.environ.keys()):
        v = os.environ.get(k, "")
        if len(v) > _WIN_ENV_LEN_LIMIT:
            oversized[k] = v
            del os.environ[k]
    yield
    for k, v in oversized.items():
        try:
            os.environ[k] = v
        except Exception:
            # 恢复失败也无所谓，进程退出后环境自然消失
            pass


@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("SSH_HOST", "192.168.1.1")
    monkeypatch.setenv("SSH_USER", "testuser")
    monkeypatch.setenv("SSH_PASSWORD", "testpass")
    monkeypatch.setenv("SSH_PORT", "22")


@pytest.fixture
def clear_env(monkeypatch):
    monkeypatch.delenv("SSH_HOST", raising=False)
    monkeypatch.delenv("SSH_USER", raising=False)
    monkeypatch.delenv("SSH_PASSWORD", raising=False)
    monkeypatch.delenv("SSH_PORT", raising=False)


@pytest.fixture
def mock_sshsession():
    """Mock SSHSession 类 - upload/download 测试用"""
    session = MagicMock()
    session.session_id = "mock-session-001"
    session.connect = AsyncMock(return_value=None)
    session.disconnect = AsyncMock(return_value=None)
    session.execute_command = AsyncMock(
        return_value={"exit_code": 0, "stdout": "mock output\n", "stderr": ""}
    )
    session.upload_file = AsyncMock(return_value={"success": True, "message": "File uploaded"})
    session.download_file = AsyncMock(return_value={"success": True, "message": "File downloaded"})

    with patch("ssh_mcp.session_manager.SSHSession", return_value=session) as mock_cls:
        yield session, mock_cls


def create_mock_args(**kwargs) -> MagicMock:
    defaults = {
        "host": None,
        "port": None,
        "username": None,
        "password": None,
        "connect_timeout": 60,
    }
    merged = {**defaults, **kwargs}
    return MagicMock(**merged)
