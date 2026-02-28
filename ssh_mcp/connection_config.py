from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


AuthMethod = Literal["password", "private_key", "agent"]


class ConnectionConfig(BaseModel):
    host: str = Field(..., description="SSH server hostname or IP address")
    port: int = Field(default=22, description="SSH server port")
    username: str = Field(..., description="SSH username")
    auth_method: AuthMethod = Field(default="private_key", description="Authentication method")
    password: Optional[str] = Field(default=None, description="SSH password (if using password auth)")
    private_key_path: Optional[Path] = Field(default=None, description="Path to private key file")
    passphrase: Optional[str] = Field(default=None, description="Passphrase for private key")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    keepalive_interval: int = Field(default=60, description="Keepalive interval in seconds")
    compress: bool = Field(default=False, description="Enable compression")
    look_for_keys: bool = Field(default=True, description="Look for keys in ~/.ssh")
    allow_agent: bool = Field(default=True, description="Use SSH agent for authentication")
    
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        return v
