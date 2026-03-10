from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from pathlib import Path


AuthMethod = Literal["password", "private_key", "agent"]
ClientType = Literal["paramiko", "asyncssh"]


class RetryConfig(BaseModel):
    """重试配置"""
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    exponential_backoff: bool = Field(default=True, description="使用指数退避")
    retry_on_timeout: bool = Field(default=True, description="超时后重试")


class ConnectionConfig(BaseModel):
    """SSH 连接配置"""
    host: str = Field(..., description="SSH server hostname or IP address")
    port: int = Field(default=22, description="SSH server port")
    username: str = Field(..., description="SSH username")
    auth_method: AuthMethod = Field(default="private_key", description="Authentication method")
    password: Optional[str] = Field(default=None, description="SSH password (if using password auth)")
    private_key_path: Optional[Path] = Field(default=None, description="Path to private key file")
    passphrase: Optional[str] = Field(default=None, description="Passphrase for private key")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    keepalive_interval: int = Field(default=30, description="Keepalive interval in seconds")
    compress: bool = Field(default=False, description="Enable compression")
    look_for_keys: bool = Field(default=False, description="Look for keys in ~/.ssh (建议关闭以强制使用配置的密钥)")
    allow_agent: bool = Field(default=False, description="Use SSH agent for authentication (建议关闭)")
    session_timeout: int = Field(default=7200, description="Session timeout in seconds (default: 2 hours)")
    client_type: ClientType = Field(default="asyncssh", description="SSH client implementation to use")
    banner_timeout: int = Field(default=60, description="Banner timeout in seconds")
    
    retry_config: Optional[RetryConfig] = Field(
        default=None, 
        description="重试配置"
    )
    
    prefer_key_auth: bool = Field(
        default=True,
        description="优先使用密钥认证（忽略密码）"
    )
    
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
    
    @field_validator("session_timeout")
    @classmethod
    def validate_session_timeout(cls, v: int) -> int:
        if v < 300:  # Minimum 5 minutes
            raise ValueError("Session timeout must be at least 5 minutes (300 seconds)")
        return v
    
    @model_validator(mode='after')
    def validate_auth_priority(self) -> 'ConnectionConfig':
        """验证认证优先级 - 密钥优先"""
        if self.prefer_key_auth:
            if self.private_key_path:
                self.auth_method = "private_key"
                self.password = None
            elif not self.password:
                raise ValueError(
                    "Private key authentication is preferred but no key path provided"
                )
        
        if self.auth_method == "private_key" and not self.private_key_path and not self.password:
            raise ValueError(
                "Private key authentication requires either private_key_path or password as fallback"
            )
        
        return self
    
    def get_retry_config(self) -> RetryConfig:
        """获取重试配置"""
        return self.retry_config or RetryConfig()
