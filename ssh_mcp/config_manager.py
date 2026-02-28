from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class SSHConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 22
    username: str = "root"
    password: str = ""
    timeout: int = 30


class ConfigManager:
    DEFAULT_CONFIG_PATH = Path.home() / ".ssh" / "mcp_config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
    
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
