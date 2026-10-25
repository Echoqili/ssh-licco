"""Security regressions; all SSH and SFTP operations are mocked."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from paramiko import RejectPolicy

from ssh_mcp.connection_config import ConnectionConfig
from ssh_mcp.handlers.connect import handle_connect
from ssh_mcp.handlers.execute import handle_execute
from ssh_mcp.handlers.file_transfer import _validate_remote_path, handle_file_transfer
from ssh_mcp.security import CommandValidator, PathValidator, SecurityError, SecurityLevel
from ssh_mcp.session_manager import SessionState, SSHSession


@pytest.fixture
def context():
    session = MagicMock()
    session.execute_command = AsyncMock(return_value={"exit_code": 0, "stdout": "", "stderr": ""})
    session.write_file = AsyncMock(return_value={"success": True})
    session.upload_file = AsyncMock(return_value={"success": True})
    return SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session=AsyncMock(return_value=session),
            create_session=AsyncMock(
                return_value=SimpleNamespace(
                    session_id="s1",
                    host="example.test",
                    port=22,
                    username="user",
                    connected_at=datetime.now(),
                )
            ),
        ),
        config_manager=MagicMock(),
        env_config={},
        logger=MagicMock(),
        audit=None,
    )


@pytest.mark.asyncio
async def test_connect_defaults_to_verified_host(context):
    await handle_connect(context, {"host": "example.test", "username": "user", "password": "test"})
    config = context.session_manager.create_session.call_args.args[0]
    assert config.strict_host_key_checking is True
    assert config.accept_new_host_key is False


@pytest.mark.asyncio
@pytest.mark.parametrize("background", [False, True])
async def test_confirmation_cannot_bypass_policy(context, background):
    validator = CommandValidator(security_level=SecurityLevel.STRICT)
    with (
        patch("ssh_mcp.handlers.execute.ensure_session", AsyncMock(return_value="s1")),
        patch("ssh_mcp.handlers.execute.command_validator", validator),
    ):
        result = await handle_execute(
            context,
            {
                "command": "unlisted_probe",
                "background": background,
                "confirm_dangerous": True,
                "confirmation_layer": 99,
            },
        )
    context.session_manager.get_session.return_value.execute_command.assert_not_awaited()
    assert "阻止" in result[0].text or "Security" in result[0].text


@pytest.mark.parametrize("command", ["ls\nprintf harmless", "ls\rprintf harmless", "ls & whoami"])
def test_balanced_blocks_shell_separators(command):
    with pytest.raises(SecurityError):
        CommandValidator().validate_command(command)


@pytest.mark.parametrize("path", ["/home/application/data", "../application/data"])
def test_base_directory_checks_components(path):
    with pytest.raises(SecurityError):
        PathValidator(base_dir="/home/app").validate_path(path)


@pytest.mark.parametrize("path", ["/home/alice/.ssh/authorized_keys", "/home/alice/.ssh", "/"])
def test_sensitive_remote_paths_rejected(path):
    assert _validate_remote_path(path, "write")[0] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "direction", ["write", "append", "upload", "download", "mkdir", "stat", "list"]
)
async def test_file_handlers_reject_sensitive_paths(context, direction):
    with patch("ssh_mcp.handlers.file_transfer.ensure_session", AsyncMock(return_value="s1")):
        result = await handle_file_transfer(
            context,
            {
                "direction": direction,
                "remote_path": "/etc/probe",
                "local_path": "probe",
                "content": "test",
            },
        )
    assert "blocked" in result[0].text.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["upload_file", "download_file"])
async def test_local_path_rejection_does_not_fall_through(method):
    config = ConnectionConfig(host="example.test", username="user", password="test")
    session = SSHSession(config)
    session._state = SessionState.CONNECTED
    session.client = MagicMock()
    session._executor = MagicMock(submit=AsyncMock(return_value={"success": True}))
    args = (
        ("/outside/forbidden", "/home/user/data")
        if method == "upload_file"
        else ("/home/user/data", "/outside/forbidden")
    )
    result = await getattr(session, method)(*args)
    assert result["success"] is False
    session._executor.submit.assert_not_awaited()


def test_paramiko_client_enforces_host_key_config():
    from ssh_mcp.clients.paramiko_client import ParamikoClient

    config = ConnectionConfig(host="example.test", username="user", password="test")
    with patch("ssh_mcp.clients.paramiko_client.SSHClient") as client_class:
        ParamikoClient(config).connect()
        client = client_class.return_value
        assert isinstance(client.set_missing_host_key_policy.call_args.args[0], RejectPolicy)
        client.load_system_host_keys.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("port", ["22; harmless_probe", 0, 65536, True])
async def test_remote_copy_validates_port(context, port):
    with patch("ssh_mcp.handlers.file_transfer.ensure_session", AsyncMock(return_value="s1")):
        result = await handle_file_transfer(
            context,
            {
                "direction": "remote_copy",
                "remote_path": "/home/user/file",
                "target_path": "/home/user/copy",
                "target_host": "example.test",
                "target_port": port,
            },
        )
    context.session_manager.get_session.return_value.execute_command.assert_not_awaited()
    assert "port" in result[0].text.lower()


@pytest.mark.parametrize("command", ["bash -c harmless", "python3 -c 'print(1)'", "eval harmless"])
def test_strict_excludes_general_execution_tools(command):
    with pytest.raises(SecurityError):
        CommandValidator(security_level=SecurityLevel.STRICT).validate_command(command)


@pytest.mark.parametrize(
    "method,args,operation",
    [
        ("_write_file_sync", ("/home/user/link", "test"), "open"),
        ("_upload_file_sync", ("probe", "/home/user/link"), "put"),
        ("_download_file_sync", ("/home/user/link", "probe"), "get"),
        ("_delete_file_sync", ("/home/user/link",), "remove"),
        ("_list_directory_sync", ("/home/user/link",), "listdir"),
        ("_stat_file_sync", ("/home/user/link",), "stat"),
        ("_make_dir_sync", ("/home/user/link",), "mkdir"),
    ],
)
def test_sftp_checks_resolved_paths(method, args, operation):
    session = SSHSession(ConnectionConfig(host="example.test", username="user", password="test"))
    session.client = MagicMock()
    sftp = session.client.open_sftp.return_value
    sftp.normalize.return_value = "/etc/probe"
    result = getattr(session, method)(*args)
    assert result["success"] is False
    getattr(sftp, operation).assert_not_called()
    sftp.close.assert_called()


def test_local_symlink_cannot_escape_root(tmp_path, monkeypatch):
    from ssh_mcp.security import validate_local_path

    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("SSH_LOCAL_BASE_DIR", str(root))
    (root / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(SecurityError):
        validate_local_path("link/outside")


def test_host_keys_loaded_when_unknown_hosts_opted_in():
    from ssh_mcp.host_keys import configure_host_keys

    client = MagicMock()
    config = ConnectionConfig(
        host="example.test", username="user", password="test", accept_new_host_key=True
    )
    configure_host_keys(client, config)
    client.load_system_host_keys.assert_called_once()


@pytest.mark.asyncio
async def test_allowed_command_still_executes(context):
    with patch("ssh_mcp.handlers.execute.ensure_session", AsyncMock(return_value="s1")):
        result = await handle_execute(context, {"command": "ls", "background": False})
    context.session_manager.get_session.return_value.execute_command.assert_awaited_once()
    assert "Exit Code: 0" in result[0].text


def test_sftp_uses_canonical_path_for_allowed_write():
    session = SSHSession(ConnectionConfig(host="example.test", username="user", password="test"))
    session.client = MagicMock()
    sftp = session.client.open_sftp.return_value
    sftp.normalize.return_value = "/home/user/data"
    with patch("ssh_mcp.security.path_validator", PathValidator(base_dir="/home/user")):
        result = session._write_file_sync("data", "hello")
    assert result["success"] is True
    sftp.open.assert_called_once_with("/home/user/data", "w")


@pytest.mark.asyncio
async def test_remote_copy_requires_trusted_host(context):
    with patch("ssh_mcp.handlers.file_transfer.ensure_session", AsyncMock(return_value="s1")):
        await handle_file_transfer(
            context,
            {
                "direction": "remote_copy",
                "remote_path": "/home/user/data",
                "target_host": "example.test",
                "target_user": "user",
                "target_path": "/home/user/copy",
            },
        )
    command = context.session_manager.get_session.return_value.execute_command.call_args.args[0]
    assert "StrictHostKeyChecking=yes" in command
    assert "sshpass" not in command


@pytest.mark.asyncio
@pytest.mark.parametrize("target_path", ["/home/user/$(probe)", "/home/user/`probe`"])
async def test_remote_copy_rejects_destination_shell_syntax(context, target_path):
    with patch("ssh_mcp.handlers.file_transfer.ensure_session", AsyncMock(return_value="s1")):
        await handle_file_transfer(
            context,
            {
                "direction": "remote_copy",
                "remote_path": "/home/user/data",
                "target_host": "example.test",
                "target_path": target_path,
            },
        )
    context.session_manager.get_session.return_value.execute_command.assert_not_awaited()
