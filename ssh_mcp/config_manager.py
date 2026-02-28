from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel


class SSHConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 22
    username: str = "root"
    password: str = ""
    timeout: int = 30


class SSHHost(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = "root"
    password: str = ""
    timeout: int = 30


class ServerConfig(BaseModel):
    ssh_hosts: List[SSHHost] = []


class ConfigManager:
    DEFAULT_CONFIG_PATH = Path.home() / ".ssh" / "mcp_config.json"
    DEFAULT_SERVER_CONFIG_PATH = Path(__file__).parent / "server.json"
    DEFAULT_HOSTS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "hosts.json"
    
    def __init__(self, config_path: Optional[Path] = None, server_config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.server_config_path = server_config_path or self.DEFAULT_SERVER_CONFIG_PATH
    
    def load(self) -> Optional[SSHConfig]:
        if not self.config_path.exists():
            return None
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SSHConfig(**data)
        except Exception:
            return None
    
    def save(self, config: SSHConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config.model_dump(), f, indent=2)
    
    @classmethod
    def get_default(cls) -> SSHConfig:
        config = cls().load()
        return config if config else SSHConfig()
    
    def load_server_config(self) -> Optional[ServerConfig]:
        # Try server.json first
        server_config_path = self.server_config_path
        if server_config_path.exists():
            try:
                with open(server_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "ssh_hosts" in data:
                    return ServerConfig(ssh_hosts=[SSHHost(**h) for h in data["ssh_hosts"]])
            except Exception:
                pass
        
        # Fallback to config/hosts.json
        hosts_config_path = self.DEFAULT_HOSTS_CONFIG_PATH
        if hosts_config_path.exists():
            try:
                with open(hosts_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "ssh_hosts" in data:
                    return ServerConfig(ssh_hosts=[SSHHost(**h) for h in data["ssh_hosts"]])
            except Exception:
                pass
        
        return None
    
    def get_host_by_name(self, name: str) -> Optional[SSHHost]:
        server_config = self.load_server_config()
        if not server_config:
            return None
        for host in server_config.ssh_hosts:
            if host.name == name:
                return host
        return None
    
    def list_hosts(self) -> List[SSHHost]:
        server_config = self.load_server_config()
        if not server_config:
            return []
        return server_config.ssh_hosts
