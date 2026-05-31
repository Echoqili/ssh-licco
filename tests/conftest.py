from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
    session.upload_file = AsyncMock(
        return_value={"success": True, "message": "File uploaded"}
    )
    session.download_file = AsyncMock(
        return_value={"success": True, "message": "File downloaded"}
    )

    with patch("ssh_mcp.session_manager.SSHSession", return_value=session) as mock_cls:
        yield session, mock_cls


@pytest.fixture
def mock_connect_and_exec():
    """Mock _connect_and_exec 函数 - exec 测试用"""
    with patch("ssh_mcp.cli._connect_and_exec") as mock:
        mock.return_value = {"exit_code": 0, "stdout": "mock output\n", "stderr": ""}
        yield mock


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