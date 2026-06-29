from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssh_mcp.config_manager import ConfigManager, SSHConfig, SSHHost, ServerConfig


class TestSSHConfig:
    def test_defaults(self):
        cfg = SSHConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 22
        assert cfg.username == "root"
        assert cfg.password == ""
        assert cfg.timeout == 30

    def test_custom_values(self):
        cfg = SSHConfig(host="10.0.0.1", port=2222, username="admin", password="secret")
        assert cfg.host == "10.0.0.1"
        assert cfg.port == 2222
        assert cfg.username == "admin"


class TestSSHHost:
    def test_defaults(self):
        host = SSHHost(name="test", host="1.2.3.4")
        assert host.name == "test"
        assert host.port == 22
        assert host.username == "root"
        assert host.keepalive_interval == 30
        assert host.session_timeout == 7200


class TestConfigManager:
    def test_load_no_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, "USER_CONFIG_PATH", tmp_path / "nonexistent.json")
        cm = ConfigManager(config_path=tmp_path / "nonexistent.json")
        result = cm.load()
        assert result is None

    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, "USER_CONFIG_PATH", tmp_path / "nonexistent.json")
        config_path = tmp_path / "ssh_config.json"
        cm = ConfigManager(config_path=config_path)
        config = SSHConfig(host="10.0.0.1", port=2222, username="admin", password="secret")
        cm.save(config)
        loaded = cm.load()
        assert loaded is not None
        assert loaded.host == "10.0.0.1"
        assert loaded.port == 2222

    def test_load_fallback_user_config(self, tmp_path, monkeypatch):
        config_path = tmp_path / "primary.json"
        user_config_path = tmp_path / "fallback.json"
        user_config_path.write_text(json.dumps({
            "host": "fallback-host",
            "port": 33,
            "username": "fallback-user",
            "password": "fallback-pass",
            "timeout": 99,
        }))
        monkeypatch.setattr(ConfigManager, "USER_CONFIG_PATH", user_config_path)
        cm = ConfigManager(config_path=config_path)
        loaded = cm.load()
        assert loaded is not None
        assert loaded.host == "fallback-host"

    def test_get_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, "USER_CONFIG_PATH", tmp_path / "nonexistent.json")
        monkeypatch.setattr(ConfigManager, "PROJECT_CONFIG_PATH", tmp_path / "nonexistent_project.json")
        default = ConfigManager.get_default()
        assert isinstance(default, SSHConfig)
        assert default.host == "127.0.0.1"

    def test_get_default_with_saved(self, tmp_path, monkeypatch):
        config_path = tmp_path / "default_config.json"
        monkeypatch.setattr(ConfigManager, "USER_CONFIG_PATH", tmp_path / "nonexistent.json")
        monkeypatch.setattr(ConfigManager, "PROJECT_CONFIG_PATH", config_path)
        cm = ConfigManager(config_path=config_path)
        cm.save(SSHConfig(host="custom-host"))
        default = ConfigManager.get_default()
        assert default.host == "custom-host"

    def test_load_server_config_no_file(self, tmp_path):
        cm = ConfigManager(
            config_path=tmp_path / "x.json",
            server_config_path=tmp_path / "server.json",
        )
        cm.DEFAULT_HOSTS_CONFIG_PATH = tmp_path / "hosts.json"
        result = cm.load_server_config()
        assert result is None

    def test_load_server_config_with_file(self, tmp_path):
        server_path = tmp_path / "server.json"
        server_path.write_text(json.dumps({
            "ssh_hosts": [
                {"name": "prod", "host": "1.2.3.4", "username": "root", "password": "pass"}
            ]
        }))
        cm = ConfigManager(
            config_path=tmp_path / "x.json",
            server_config_path=server_path,
        )
        result = cm.load_server_config()
        assert result is not None
        assert len(result.ssh_hosts) == 1
        assert result.ssh_hosts[0].name == "prod"

    def test_get_host_by_name(self, tmp_path):
        server_path = tmp_path / "server.json"
        server_path.write_text(json.dumps({
            "ssh_hosts": [
                {"name": "prod", "host": "1.2.3.4", "username": "root", "password": "pass"},
                {"name": "dev", "host": "5.6.7.8", "username": "dev", "password": "devpass"},
            ]
        }))
        cm = ConfigManager(
            config_path=tmp_path / "x.json",
            server_config_path=server_path,
        )
        host = cm.get_host_by_name("prod")
        assert host is not None
        assert host.host == "1.2.3.4"

    def test_get_host_by_name_not_found(self, tmp_path):
        server_path = tmp_path / "server.json"
        server_path.write_text(json.dumps({"ssh_hosts": []}))
        cm = ConfigManager(
            config_path=tmp_path / "x.json",
            server_config_path=server_path,
        )
        host = cm.get_host_by_name("nonexistent")
        assert host is None

    def test_list_hosts(self, tmp_path):
        server_path = tmp_path / "server.json"
        server_path.write_text(json.dumps({
            "ssh_hosts": [
                {"name": "prod", "host": "1.2.3.4", "username": "root"},
                {"name": "dev", "host": "5.6.7.8", "username": "dev"},
            ]
        }))
        cm = ConfigManager(
            config_path=tmp_path / "x.json",
            server_config_path=server_path,
        )
        hosts = cm.list_hosts()
        assert len(hosts) == 2

    def test_add_host(self, tmp_path):
        hosts_path = tmp_path / "hosts.json"
        cm = ConfigManager(config_path=tmp_path / "x.json")
        cm.DEFAULT_HOSTS_CONFIG_PATH = hosts_path
        new_host = SSHHost(name="staging", host="10.0.0.1", username="deploy")
        cm.add_host(new_host)
        assert hosts_path.exists()
        data = json.loads(hosts_path.read_text())
        assert len(data["ssh_hosts"]) == 1
        assert data["ssh_hosts"][0]["name"] == "staging"

    def test_add_host_updates_existing(self, tmp_path):
        hosts_path = tmp_path / "hosts.json"
        hosts_path.write_text(json.dumps({
            "ssh_hosts": [{"name": "staging", "host": "10.0.0.1", "username": "deploy", "password": "", "timeout": 30, "keepalive_interval": 30, "session_timeout": 7200, "banner_timeout": 60}]
        }))
        cm = ConfigManager(config_path=tmp_path / "x.json")
        cm.DEFAULT_HOSTS_CONFIG_PATH = hosts_path
        updated = SSHHost(name="staging", host="10.0.0.2", username="newdeploy")
        cm.add_host(updated)
        data = json.loads(hosts_path.read_text())
        assert len(data["ssh_hosts"]) == 1
        assert data["ssh_hosts"][0]["host"] == "10.0.0.2"

    def test_remove_host(self, tmp_path):
        hosts_path = tmp_path / "hosts.json"
        hosts_path.write_text(json.dumps({
            "ssh_hosts": [
                {"name": "prod", "host": "1.2.3.4", "username": "root", "password": "", "timeout": 30, "keepalive_interval": 30, "session_timeout": 7200, "banner_timeout": 60},
                {"name": "dev", "host": "5.6.7.8", "username": "dev", "password": "", "timeout": 30, "keepalive_interval": 30, "session_timeout": 7200, "banner_timeout": 60},
            ]
        }))
        cm = ConfigManager(config_path=tmp_path / "x.json")
        cm.DEFAULT_HOSTS_CONFIG_PATH = hosts_path
        result = cm.remove_host("prod")
        assert result is True
        data = json.loads(hosts_path.read_text())
        assert len(data["ssh_hosts"]) == 1
        assert data["ssh_hosts"][0]["name"] == "dev"

    def test_remove_host_not_found(self, tmp_path):
        hosts_path = tmp_path / "hosts.json"
        hosts_path.write_text(json.dumps({"ssh_hosts": []}))
        cm = ConfigManager(config_path=tmp_path / "x.json")
        cm.DEFAULT_HOSTS_CONFIG_PATH = hosts_path
        result = cm.remove_host("nonexistent")
        assert result is False

    def test_remove_host_no_file(self, tmp_path):
        cm = ConfigManager(config_path=tmp_path / "x.json")
        cm.DEFAULT_HOSTS_CONFIG_PATH = tmp_path / "nonexistent.json"
        result = cm.remove_host("test")
        assert result is False
