from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ssh_mcp.connection_config import ConnectionConfig
from ssh_mcp.exceptions import ConnectionException
from ssh_mcp.session_manager import SSHSession, SessionManager, SessionState, SessionInfo


@pytest.fixture
def conn_config():
    return ConnectionConfig(
        host="1.2.3.4",
        port=22,
        username="root",
        password="testpass",
        auth_method="password",
        accept_new_host_key=True,
    )


class TestSessionState:
    def test_values(self):
        assert SessionState.CONNECTING.value == "connecting"
        assert SessionState.CONNECTED.value == "connected"
        assert SessionState.DISCONNECTED.value == "disconnected"
        assert SessionState.ERROR.value == "error"


class TestSSHSession:
    def test_initial_state(self, conn_config):
        session = SSHSession(conn_config)
        assert session.state == SessionState.DISCONNECTED
        assert session.is_connected is False
        assert session.session_id is not None

    @pytest.mark.asyncio
    async def test_connect_success(self, conn_config):
        session = SSHSession(conn_config)
        mock_executor = MagicMock()

        async def mock_submit(func, *args, **kwargs):
            session.client = MagicMock()
            return None

        mock_executor.submit = AsyncMock(side_effect=mock_submit)
        with patch.object(session, '_executor', mock_executor), \
             patch.object(session, '_start_keepalive', new_callable=AsyncMock):
            info = await session.connect()
        assert session.is_connected is True
        assert info.host == "1.2.3.4"
        assert info.state == SessionState.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, conn_config):
        session = SSHSession(conn_config)
        session._state = SessionState.CONNECTED
        session.client = MagicMock()
        info = await session.connect()
        assert info.state == SessionState.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_failure(self, conn_config):
        session = SSHSession(conn_config)
        mock_executor = MagicMock()
        mock_executor.submit = AsyncMock(side_effect=Exception("connection refused"))
        with patch.object(session, '_executor', mock_executor):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await session.connect()
        assert session.state == SessionState.ERROR

    @pytest.mark.asyncio
    async def test_disconnect(self, conn_config):
        session = SSHSession(conn_config)
        mock_executor = MagicMock()

        async def mock_submit(func, *args, **kwargs):
            session.client = MagicMock()
            return None

        mock_executor.submit = AsyncMock(side_effect=mock_submit)
        with patch.object(session, '_executor', mock_executor), \
             patch.object(session, '_start_keepalive', new_callable=AsyncMock):
            await session.connect()
        mock_ssh = MagicMock()
        session.client = mock_ssh
        await session.disconnect()
        assert session.state == SessionState.DISCONNECTED
        assert session.client is None

    @pytest.mark.asyncio
    async def test_execute_not_connected(self, conn_config):
        session = SSHSession(conn_config)
        with pytest.raises(ConnectionError, match="Not connected"):
            await session.execute_command("ls")

    @pytest.mark.asyncio
    async def test_upload_not_connected(self, conn_config):
        session = SSHSession(conn_config)
        with pytest.raises(ConnectionError, match="Not connected"):
            await session.upload_file("/local", "/remote")

    @pytest.mark.asyncio
    async def test_download_not_connected(self, conn_config):
        session = SSHSession(conn_config)
        with pytest.raises(ConnectionError, match="Not connected"):
            await session.download_file("/remote", "/local")

    @pytest.mark.asyncio
    async def test_list_directory_not_connected(self, conn_config):
        session = SSHSession(conn_config)
        with pytest.raises(ConnectionError, match="Not connected"):
            await session.list_directory("/tmp")


class TestSessionManager:
    @pytest.mark.asyncio
    async def test_create_session(self, conn_config):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"
        mock_session.config = conn_config
        mock_session.connect = AsyncMock(return_value=MagicMock(
            session_id="test-session-id",
            host="1.2.3.4",
            port=22,
            username="root",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        ))
        with patch("ssh_mcp.session_manager.SSHSession", return_value=mock_session):
            info = await manager.create_session(conn_config)
        assert info.session_id == "test-session-id"

    @pytest.mark.asyncio
    async def test_get_session(self):
        manager = SessionManager()
        mock_session = MagicMock()
        manager._sessions["sess-1"] = mock_session
        result = await manager.get_session("sess-1")
        assert result is mock_session

    @pytest.mark.asyncio
    async def test_get_session_disconnected_auto_clean(self):
        """get_session 遇到已断开的 session 时，应自动清理并返回 None（不抛 AttributeError）"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.is_connected = False
        mock_session.config.host = "1.2.3.4"
        # 让重连计数已达上限，走"清理并返回 None"分支（避免 MagicMock 比较 '>=' 报错）
        mock_session._reconnect_count = 99
        mock_session._max_reconnects = 1
        # disconnect 是协程，需用 AsyncMock
        mock_session.disconnect = AsyncMock(return_value=None)
        manager._sessions["dead-id"] = mock_session
        result = await manager.get_session("dead-id")
        assert result is None
        assert "dead-id" not in manager._sessions

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        manager = SessionManager()
        result = await manager.get_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_close_session(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock()
        manager._sessions["sess-1"] = mock_session
        await manager.close_session("sess-1")
        assert "sess-1" not in manager._sessions

    @pytest.mark.asyncio
    async def test_close_all_sessions(self):
        manager = SessionManager()
        mock1 = MagicMock()
        mock1.disconnect = AsyncMock()
        mock2 = MagicMock()
        mock2.disconnect = AsyncMock()
        manager._sessions["s1"] = mock1
        manager._sessions["s2"] = mock2
        await manager.close_all_sessions()
        assert len(manager._sessions) == 0

    def test_list_sessions(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session._get_session_info.return_value = MagicMock()
        manager._sessions["s1"] = mock_session
        sessions = manager.list_sessions()
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_max_sessions_limit(self, conn_config):
        manager = SessionManager()
        for i in range(manager.MAX_SESSIONS):
            mock_s = MagicMock()
            mock_s.config = conn_config
            mock_s.is_connected = True
            mock_s.disconnect = AsyncMock()
            manager._sessions[f"s-{i}"] = mock_s
        with pytest.raises(ConnectionException, match="会话数限制"):
            await manager.create_session(conn_config, reuse=False)

    @pytest.mark.asyncio
    async def test_max_sessions_per_host(self, conn_config):
        manager = SessionManager()
        for i in range(manager.MAX_SESSIONS_PER_HOST):
            mock_s = MagicMock()
            mock_s.config = conn_config
            mock_s.is_connected = True
            mock_s.disconnect = AsyncMock()
            manager._sessions[f"s-{i}"] = mock_s
        with pytest.raises(ConnectionException, match="会话数限制"):
            await manager.create_session(conn_config, reuse=False)

    @pytest.mark.asyncio
    async def test_reuse_existing_session(self, conn_config):
        """同一主机+用户已有活跃会话时，复用而非创建新会话"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.config = conn_config
        mock_session.is_connected = True
        mock_session._get_session_info.return_value = SessionInfo(
            session_id="reused-id",
            host="192.168.1.100",
            port=22,
            username="root",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        manager._sessions["reused-id"] = mock_session

        info = await manager.create_session(conn_config)
        assert info.session_id == "reused-id"
        # 不应创建新会话
        assert len(manager._sessions) == 1

    @pytest.mark.asyncio
    async def test_reuse_disabled_creates_new(self, conn_config):
        """reuse=False 时强制创建新会话"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.config = conn_config
        mock_session.is_connected = True
        mock_session._get_session_info.return_value = SessionInfo(
            session_id="old-id",
            host="192.168.1.100",
            port=22,
            username="root",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        manager._sessions["old-id"] = mock_session

        new_mock = MagicMock()
        new_mock.config = conn_config
        new_mock.is_connected = True
        new_mock.connect = AsyncMock(return_value=SessionInfo(
            session_id="new-id",
            host="192.168.1.100",
            port=22,
            username="root",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        ))
        with patch("ssh_mcp.session_manager.SSHSession", return_value=new_mock):
            info = await manager.create_session(conn_config, reuse=False)
        assert info.session_id == "new-id"
        assert len(manager._sessions) == 2

    @pytest.mark.asyncio
    async def test_no_reuse_disconnected_session(self, conn_config):
        """已断开的会话不应被复用"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.config = conn_config
        mock_session.is_connected = False  # 已断开
        manager._sessions["dead-id"] = mock_session

        new_mock = MagicMock()
        new_mock.config = conn_config
        new_mock.is_connected = True
        new_mock.connect = AsyncMock(return_value=SessionInfo(
            session_id="new-id",
            host="192.168.1.100",
            port=22,
            username="root",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        ))
        with patch("ssh_mcp.session_manager.SSHSession", return_value=new_mock):
            info = await manager.create_session(conn_config)
        assert info.session_id == "new-id"

    @pytest.mark.asyncio
    async def test_no_reuse_different_user(self, conn_config):
        """不同用户不应复用会话"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.config = conn_config  # username="root"
        mock_session.is_connected = True
        manager._sessions["s1"] = mock_session

        other_config = ConnectionConfig(
            host="192.168.1.100", username="admin", password="pwd"
        )
        new_mock = MagicMock()
        new_mock.config = other_config
        new_mock.is_connected = True
        new_mock.connect = AsyncMock(return_value=SessionInfo(
            session_id="new-id",
            host="192.168.1.100",
            port=22,
            username="admin",
            state=SessionState.CONNECTED,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        ))
        with patch("ssh_mcp.session_manager.SSHSession", return_value=new_mock):
            info = await manager.create_session(other_config)
        assert info.session_id == "new-id"

    @pytest.mark.asyncio
    async def test_execute_command_delegates(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.execute_command = AsyncMock(return_value={"exit_code": 0, "stdout": "ok", "stderr": ""})
        manager._sessions["s1"] = mock_session
        result = await manager.execute_command("s1", "ls")
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_command_session_not_found(self):
        manager = SessionManager()
        with pytest.raises(ConnectionError, match="not found"):
            await manager.execute_command("nonexistent", "ls")

    @pytest.mark.asyncio
    async def test_upload_file_delegates(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.upload_file = AsyncMock(return_value={"success": True})
        manager._sessions["s1"] = mock_session
        result = await manager.upload_file("s1", "/local", "/remote")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_download_file_delegates(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.download_file = AsyncMock(return_value={"success": True})
        manager._sessions["s1"] = mock_session
        result = await manager.download_file("s1", "/remote", "/local")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_directory_delegates(self):
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.list_directory = AsyncMock(return_value={"success": True, "files": []})
        manager._sessions["s1"] = mock_session
        result = await manager.list_directory("s1", "/tmp")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        manager = SessionManager()
        mock1 = MagicMock()
        mock1.disconnect = AsyncMock()
        manager._sessions["s1"] = mock1
        await manager.shutdown()
        assert len(manager._sessions) == 0
