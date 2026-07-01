from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ssh_mcp.handlers.connect import handle_connect, handle_disconnect
from ssh_mcp.handlers.docker import handle_docker
from ssh_mcp.handlers.execute import handle_execute
from ssh_mcp.handlers.file_transfer import handle_file_transfer
from ssh_mcp.handlers.host import handle_host
from ssh_mcp.handlers.key import handle_generate_key
from ssh_mcp.handlers.utils import should_run_background
from ssh_mcp.server import SSHMCPServer


@pytest.fixture
def server():
    with patch.dict(os.environ, {}, clear=False):
        for key in ["SSH_HOST", "SSH_PORT", "SSH_USER", "SSH_PASSWORD",
                     "SSH_RATE_LIMIT", "SSH_AUDIT_LOG_PATH"]:
            os.environ.pop(key, None)
        with patch("ssh_mcp.server.SessionManager"), \
             patch("ssh_mcp.server.KeyManager"), \
             patch("ssh_mcp.server.ConfigManager"):
            srv = SSHMCPServer()
    return srv


class TestSSHMCPServerInit:
    def test_server_created(self, server):
        assert server is not None
        assert server.session_manager is not None
        assert server.key_manager is not None
        assert server.config_manager is not None

    def test_rate_limit_defaults(self, server):
        assert server._rate_limit_enabled is True
        assert server._rate_limit_max == 30
        assert server._rate_limit_window == 60


class TestRateLimit:
    def test_rate_limit_allows(self, server):
        server._rate_limit_enabled = True
        server._command_timestamps = []
        allowed, msg = server._check_rate_limit()
        assert allowed is True
        assert msg == ""

    def test_rate_limit_blocks(self, server):
        server._rate_limit_enabled = True
        server._rate_limit_max = 2
        server._command_timestamps = []
        import time
        server._command_timestamps = [time.time(), time.time()]
        allowed, msg = server._check_rate_limit()
        assert allowed is False
        assert "limit" in msg.lower() or "频率" in msg

    def test_rate_limit_disabled(self, server):
        server._rate_limit_enabled = False
        allowed, msg = server._check_rate_limit()
        assert allowed is True


class TestLoadEnvConfig:
    def test_no_env_vars(self, server):
        assert server._env_config == {}

    def test_with_env_vars(self):
        with patch.dict(os.environ, {
            "SSH_HOST": "10.0.0.1",
            "SSH_PORT": "2222",
            "SSH_USER": "admin",
            "SSH_PASSWORD": "secret",
        }):
            with patch("ssh_mcp.server.SessionManager"), \
                 patch("ssh_mcp.server.KeyManager"), \
                 patch("ssh_mcp.server.ConfigManager"):
                srv = SSHMCPServer()
            assert srv._env_config["host"] == "10.0.0.1"
            assert srv._env_config["port"] == 2222


class TestHandleConfig:
    """v1.2.2: _handle_config merged into _handle_connect with save_config=True"""

    @pytest.mark.asyncio
    async def test_save_config(self, server):
        server.config_manager = MagicMock()
        mock_session_info = MagicMock()
        mock_session_info.session_id = "cfg-test"
        mock_session_info.host = "1.2.3.4"
        mock_session_info.port = 22
        mock_session_info.username = "root"
        mock_session_info.connected_at = MagicMock()
        mock_session_info.connected_at.isoformat.return_value = "2024-01-01T00:00:00"
        server.session_manager.create_session = AsyncMock(return_value=mock_session_info)
        result = await handle_connect(server._ctx, {
            "host": "1.2.3.4",
            "port": 22,
            "username": "root",
            "password": "secret",
            "timeout": 30,
            "save_config": True,
        })
        assert len(result) == 1
        assert "saved" in result[0].text.lower() or "Config saved" in result[0].text

    @pytest.mark.asyncio
    async def test_save_config_env_password(self, server):
        server.config_manager = MagicMock()
        mock_session_info = MagicMock()
        mock_session_info.session_id = "cfg-test"
        mock_session_info.host = "1.2.3.4"
        mock_session_info.port = 22
        mock_session_info.username = "root"
        mock_session_info.connected_at = MagicMock()
        mock_session_info.connected_at.isoformat.return_value = "2024-01-01T00:00:00"
        server.session_manager.create_session = AsyncMock(return_value=mock_session_info)
        with patch.dict(os.environ, {"SSH_PASSWORD": "env_pass"}):
            result = await handle_connect(server._ctx, {
                "host": "1.2.3.4",
                "port": 22,
                "username": "root",
                "password": "env_pass",
                "timeout": 30,
                "save_config": True,
            })
        assert len(result) == 1


class TestHandleDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect(self, server):
        server.session_manager = MagicMock()
        server.session_manager.close_session = AsyncMock()
        result = await handle_disconnect(server._ctx, {"session_id": "sess-1"})
        assert len(result) == 1
        assert "closed" in result[0].text.lower()


class TestHandleListSessions:
    """v1.2.2: _handle_list_sessions merged into _handle_disconnect (no session_id → lists sessions)"""

    @pytest.mark.asyncio
    async def test_no_sessions(self, server):
        server.session_manager = MagicMock()
        server.session_manager.list_sessions.return_value = []
        result = await handle_disconnect(server._ctx, {})
        assert len(result) == 1
        assert "no" in result[0].text.lower() or "No" in result[0].text

    @pytest.mark.asyncio
    async def test_with_sessions(self, server):
        server.session_manager = MagicMock()
        mock_info = MagicMock()
        mock_info.session_id = "s1"
        mock_info.host = "1.2.3.4"
        mock_info.port = 22
        mock_info.username = "root"
        mock_info.state.value = "connected"
        mock_info.connected_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_info.last_activity.isoformat.return_value = "2024-01-01T00:01:00"
        server.session_manager.list_sessions.return_value = [mock_info]
        result = await handle_disconnect(server._ctx, {})
        assert len(result) == 1
        assert "s1" in result[0].text


class TestHandleGenerateKey:
    @pytest.mark.asyncio
    async def test_generate_ed25519(self, server):
        from ssh_mcp.key_manager import SSHKeyPair
        mock_kp = SSHKeyPair(
            private_key="priv", public_key="ssh-ed25519 AAAA",
            key_type="ed25519", fingerprint="SHA256:abc",
        )
        server.key_manager = MagicMock()
        server.key_manager.generate_ed25519_key.return_value = mock_kp
        result = await handle_generate_key(server._ctx, {"key_type": "ed25519"})
        assert len(result) == 1
        assert "ed25519" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_rsa(self, server):
        from ssh_mcp.key_manager import SSHKeyPair
        mock_kp = SSHKeyPair(
            private_key="priv", public_key="ssh-rsa AAAA",
            key_type="rsa", fingerprint="SHA256:abc",
        )
        server.key_manager = MagicMock()
        server.key_manager.generate_rsa_key.return_value = mock_kp
        result = await handle_generate_key(server._ctx, {"key_type": "rsa", "key_size": 4096})
        assert len(result) == 1
        assert "rsa" in result[0].text


class TestHandleFileTransfer:
    @pytest.mark.asyncio
    async def test_session_not_found(self, server):
        server.session_manager = MagicMock()
        server.session_manager.get_session = AsyncMock(return_value=None)
        result = await handle_file_transfer(server._ctx, {
            "session_id": "nonexistent",
            "local_path": "/local",
            "remote_path": "/remote",
            "direction": "upload",
        })
        assert len(result) == 1
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_upload(self, server):
        mock_session = MagicMock()
        mock_session.upload_file = AsyncMock(return_value={"success": True, "message": "Uploaded"})
        server.session_manager = MagicMock()
        server.session_manager.get_session = AsyncMock(return_value=mock_session)
        result = await handle_file_transfer(server._ctx, {
            "session_id": "s1",
            "local_path": "/local",
            "remote_path": "/remote",
            "direction": "upload",
        })
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_download(self, server):
        mock_session = MagicMock()
        mock_session.download_file = AsyncMock(return_value={"success": True, "message": "Downloaded"})
        server.session_manager = MagicMock()
        server.session_manager.get_session = AsyncMock(return_value=mock_session)
        result = await handle_file_transfer(server._ctx, {
            "session_id": "s1",
            "local_path": "/local",
            "remote_path": "/remote",
            "direction": "download",
        })
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_unknown_direction(self, server):
        mock_session = MagicMock()
        server.session_manager = MagicMock()
        server.session_manager.get_session = AsyncMock(return_value=mock_session)
        result = await handle_file_transfer(server._ctx, {
            "session_id": "s1",
            "local_path": "/local",
            "remote_path": "/remote",
            "direction": "invalid",
        })
        assert len(result) == 1
        assert "unknown" in result[0].text.lower() or "Unknown" in result[0].text


class TestHandleListHosts:
    """v1.2.2: _handle_list_hosts → _handle_host({"action": "list"})"""

    @pytest.mark.asyncio
    async def test_list_hosts(self, server):
        server.config_manager = MagicMock()
        server.config_manager.list_hosts.return_value = []
        result = await handle_host(server._ctx, {"action": "list"})
        assert len(result) == 1


class TestHandleAddHost:
    """v1.2.2: _handle_add_host → _handle_host({"action": "add", ...})"""

    @pytest.mark.asyncio
    async def test_add_host(self, server):
        server.config_manager = MagicMock()
        result = await handle_host(server._ctx, {
            "action": "add",
            "name": "prod",
            "host": "1.2.3.4",
            "port": 22,
            "username": "root",
            "password": "",
            "timeout": 60,
        })
        assert len(result) == 1
        assert "added" in result[0].text.lower() or "添加" in result[0].text

    @pytest.mark.asyncio
    async def test_add_host_missing_name(self, server):
        server.config_manager = MagicMock()
        result = await handle_host(server._ctx, {
            "action": "add",
            "name": None,
            "host": "1.2.3.4",
        })
        assert len(result) == 1
        assert "error" in result[0].text.lower() or "错误" in result[0].text


class TestHandleRemoveHost:
    """v1.2.2: _handle_remove_host → _handle_host({"action": "remove", ...})"""

    @pytest.mark.asyncio
    async def test_remove_host(self, server):
        server.config_manager = MagicMock()
        server.config_manager.remove_host.return_value = True
        result = await handle_host(server._ctx, {"action": "remove", "name": "prod"})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_remove_host_not_found(self, server):
        server.config_manager = MagicMock()
        server.config_manager.remove_host.return_value = False
        result = await handle_host(server._ctx, {"action": "remove", "name": "nonexistent"})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_remove_host_no_name(self, server):
        server.config_manager = MagicMock()
        result = await handle_host(server._ctx, {"action": "remove", "name": None})
        assert len(result) == 1


class TestShouldRunBackground:
    def test_docker_ps_not_background(self, server):
        assert should_run_background("docker ps") is False

    def test_docker_images_not_background(self, server):
        assert should_run_background("docker images") is False

    def test_docker_logs_not_background(self, server):
        assert should_run_background("docker logs mycontainer") is False

    def test_python_app_background(self, server):
        assert should_run_background("python app.py") is True

    def test_npm_start_background(self, server):
        assert should_run_background("npm start") is True

    def test_docker_compose_up_background(self, server):
        assert should_run_background("docker-compose up") is True

    def test_simple_ls_not_background(self, server):
        assert should_run_background("ls -la") is False

    def test_java_jar_background(self, server):
        assert should_run_background("java -jar app.jar") is True

    def test_go_run_background(self, server):
        assert should_run_background("go run main.go") is True

    def test_cargo_run_background(self, server):
        assert should_run_background("cargo run") is True

    def test_flask_run_background(self, server):
        assert should_run_background("flask run") is True

    def test_systemctl_start_background(self, server):
        assert should_run_background("systemctl start nginx") is True

    def test_docker_stop_not_background(self, server):
        assert should_run_background("docker stop mycontainer") is False

    def test_docker_exec_not_background(self, server):
        assert should_run_background("docker exec -it mycontainer bash") is False


class TestHandleExecute:
    @pytest.mark.asyncio
    async def test_security_blocked(self, server):
        result = await handle_execute(server._ctx, {
            "session_id": "s1",
            "command": "evil_command arg1",
            "timeout": 30,
            "background": False,
        })
        assert len(result) == 1
        assert "blocked" in result[0].text.lower() or "阻止" in result[0].text

    @pytest.mark.asyncio
    async def test_session_not_found(self, server):
        server.session_manager = MagicMock()
        server.session_manager.get_session = AsyncMock(return_value=None)
        result = await handle_execute(server._ctx, {
            "session_id": "nonexistent",
            "command": "ls",
            "timeout": 30,
            "background": False,
        })
        assert len(result) == 1
        assert "not found" in result[0].text.lower()


class TestHandleDockerBuild:
    """v1.2.2: _handle_docker_build → _handle_docker({"action": "build", ...})"""

    @pytest.mark.asyncio
    async def test_missing_session_id(self, server):
        result = await handle_docker(server._ctx, {
            "action": "build",
            "session_id": None,
            "image_name": "myapp:latest",
        })
        assert len(result) == 1
        # 无 session 时返回 "No session_id, name, host, or SSH_HOST env var configured."
        assert "session" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_image_name(self, server):
        result = await handle_docker(server._ctx, {
            "action": "build",
            "session_id": "s1",
            "image_name": None,
        })
        assert len(result) == 1


class TestHandleDockerStatus:
    """v1.2.2: _handle_docker_status → _handle_docker({"action": "ps", ...})"""

    @pytest.mark.asyncio
    async def test_missing_session_id(self, server):
        result = await handle_docker(server._ctx, {
            "action": "ps",
            "session_id": None,
        })
        assert len(result) == 1
        assert "session" in result[0].text.lower() or "error" in result[0].text.lower()


class TestHandleExecuteWait:
    """v1.2.2: _handle_execute_wait merged into _handle_execute"""

    @pytest.mark.asyncio
    async def test_missing_params(self, server):
        server._env_config = {}
        result = await handle_execute(server._ctx, {
            "session_id": None,
            "command": "echo test",
            "timeout": 60,
        })
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_security_blocked(self, server):
        result = await handle_execute(server._ctx, {
            "session_id": "s1",
            "command": "evil_command arg1",
            "timeout": 60,
        })
        assert len(result) == 1


class TestHandleContainerLogs:
    """v1.2.2: _handle_container_logs → _handle_docker({"action": "logs", ...})"""

    @pytest.mark.asyncio
    async def test_missing_params(self, server):
        result = await handle_docker(server._ctx, {
            "action": "logs",
            "session_id": None,
            "container_name": None,
        })
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invalid_container_name(self, server):
        result = await handle_docker(server._ctx, {
            "action": "logs",
            "session_id": "s1",
            "container_name": "invalid;name",
        })
        assert len(result) == 1
        assert "invalid" in result[0].text.lower() or "无效" in result[0].text


class TestHandleBackgroundTask:
    """v1.2.2: _handle_background_task merged into _handle_execute (background=True)"""

    @pytest.mark.asyncio
    async def test_missing_params(self, server):
        server._env_config = {}
        result = await handle_execute(server._ctx, {
            "session_id": None,
            "command": "echo test",
            "background": True,
        })
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_instant_command_not_auto_background(self, server):
        # "docker ps" should NOT be auto-detected as background
        server.session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.execute_command = AsyncMock(return_value={
            "exit_code": 0, "stdout": "CONTAINER ID", "stderr": ""
        })
        server.session_manager.get_session = AsyncMock(return_value=mock_session)
        result = await handle_execute(server._ctx, {
            "session_id": "s1",
            "command": "docker ps",
        })
        assert len(result) == 1
        assert "Exit Code: 0" in result[0].text


class TestHandleTaskStatus:
    """v1.2.2: _handle_task_status merged into _handle_execute"""

    @pytest.mark.asyncio
    async def test_missing_session_id(self, server):
        server._env_config = {}
        result = await handle_execute(server._ctx, {
            "session_id": None,
            "command": "echo test",
            "wait": True,
        })
        assert len(result) == 1
