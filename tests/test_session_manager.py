from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
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
        """get_session 遇到非真实 SSHSession 对象（如测试 Mock）时，应清理并返回 None"""
        manager = SessionManager()
        mock_session = MagicMock()
        mock_session.is_connected = False
        mock_session.config.host = "1.2.3.4"
        # MagicMock 不是 SSHSession 实例，走"跳过重连并清理"分支
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
    async def test_get_session_dead_transparent_rebuild(self, conn_config):
        """死会话透明重建：复用原 session_id、成功后连续失败计数清零（不再删除 entry）"""

        class FakeSession(SSHSession):
            async def connect(self):
                self._state = SessionState.CONNECTED
                self.client = MagicMock()
                return self._get_session_info()

        manager = SessionManager()
        # dead 必须是 FakeSession 实例（不调用 connect 即保持断开态），
        # 否则补丁后 isinstance 检查会走清理分支
        dead = FakeSession(conn_config)
        dead._reconnect_count = 99  # 即使远超旧的重连上限也应重建
        manager._sessions["sid"] = dead

        with patch("ssh_mcp.session_manager.SSHSession", FakeSession):
            result = await manager.get_session("sid")

        assert isinstance(result, FakeSession)
        assert result is not dead  # 底层对象已替换
        assert result.session_id == "sid"  # 调用方持有的 session_id 保持有效
        assert manager._sessions["sid"] is result
        assert result._reconnect_count == 0

    @pytest.mark.asyncio
    async def test_get_session_rebuild_failure_keeps_entry(self, conn_config):
        """重建失败不删除 entry：session_id 保留，主机恢复后下次调用重建成功"""

        class FlakySession(SSHSession):
            fail_connect = True

            async def connect(self):
                if type(self).fail_connect:
                    raise ConnectionError("host unreachable")
                self._state = SessionState.CONNECTED
                self.client = MagicMock()
                return self._get_session_info()

        manager = SessionManager()
        dead = FlakySession(conn_config)  # 未连接 → 死会话
        manager._sessions["sid"] = dead

        with patch("ssh_mcp.session_manager.SSHSession", FlakySession):
            # 阶段一：主机不可达，重建失败但 entry 保留
            result = await manager.get_session("sid")
            assert result is None
            assert manager._sessions["sid"] is dead  # entry 保留供后续重试
            assert dead._reconnect_count == 1  # 连续失败计数累加（日志观察用）

            # 阶段二：主机恢复，同一 session_id 透明重建成功
            FlakySession.fail_connect = False
            result = await manager.get_session("sid")
            assert result is not None
            assert result.session_id == "sid"
            assert manager._sessions["sid"] is result

    @pytest.mark.asyncio
    async def test_get_session_live_resets_reconnect_count(self, conn_config):
        """存活会话被正常获取时重置连续失败计数，历史抖动不累计"""
        manager = SessionManager()
        live = SSHSession(conn_config)
        live._state = SessionState.CONNECTED
        live.client = MagicMock()
        live._reconnect_count = 2
        manager._sessions["sid"] = live

        result = await manager.get_session("sid")
        assert result is live
        assert live._reconnect_count == 0

    @pytest.mark.asyncio
    async def test_create_session_dead_entries_do_not_count_toward_limit(self, conn_config):
        """dead entry 不占用并发额度：同主机多个死会话不应阻止新建"""

        class FakeSession(SSHSession):
            async def connect(self):
                self._state = SessionState.CONNECTED
                self.client = MagicMock()
                return self._get_session_info()

        manager = SessionManager()
        for i in range(manager.MAX_SESSIONS_PER_HOST):
            dead = SSHSession(conn_config)  # 从未连接 → 死会话
            manager._sessions[f"dead-{i}"] = dead

        with patch("ssh_mcp.session_manager.SSHSession", FakeSession):
            info = await manager.create_session(conn_config)  # 不应抛 ConnectionException

        assert info.session_id in manager._sessions

    @pytest.mark.asyncio
    async def test_cleanup_timeout_sessions_reaps_dead_entries(self, conn_config):
        """dead entry 超过 idle 超时后由清理循环兜底回收，不会永久滞留"""
        manager = SessionManager()
        dead = SSHSession(conn_config)
        dead._last_activity = datetime.now() - timedelta(
            seconds=conn_config.session_timeout + 100
        )
        manager._sessions["sid"] = dead

        await manager._cleanup_timeout_sessions()
        assert "sid" not in manager._sessions

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
