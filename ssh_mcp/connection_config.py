from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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
    auth_method: AuthMethod | None = Field(default=None, description="Authentication method (auto-detected if not provided)")
    password: str | None = Field(default=None, description="SSH password (if using password auth)")
    private_key_path: Path | None = Field(default=None, description="Path to private key file")
    passphrase: str | None = Field(default=None, description="Passphrase for private key")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    keepalive_interval: int = Field(default=30, description="Keepalive interval in seconds")
    compress: bool = Field(default=False, description="Enable compression")
    look_for_keys: bool = Field(default=False, description="Look for keys in ~/.ssh (建议关闭以强制使用配置的密钥)")
    allow_agent: bool = Field(default=False, description="Use SSH agent for authentication (建议关闭)")
    session_timeout: int = Field(default=7200, description="Session timeout in seconds (default: 2 hours)")
    client_type: ClientType = Field(default="asyncssh", description="SSH client implementation to use")
    banner_timeout: int = Field(default=60, description="Banner timeout in seconds")

    retry_config: RetryConfig | None = Field(
        default=None,
        description="重试配置"
    )

    prefer_key_auth: bool = Field(
        default=True,
        description="优先使用密钥认证（忽略密码）"
    )

    # 🔒 Host Key 安全配置
    known_hosts_path: Path | None = Field(
        default=None,
        description="已知主机密钥文件路径 (默认: ~/.ssh/known_hosts)"
    )
    strict_host_key_checking: bool = Field(
        default=True,
        description="是否启用严格主机密钥验证 (生产环境必须开启)"
    )
    # ⚠️ 仅在测试环境使用：跳过主机密钥验证（等同于 MITM 攻击）
    # 设置为 True 时会接受任意主机密钥，请仅在可控环境中使用
    accept_new_host_key: bool = Field(
        default=False,
        description="⚠️ 危险：是否自动接受新主机密钥 (默认 False). 仅测试环境使用"
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
    def validate_auth_priority(self) -> ConnectionConfig:
        """验证认证配置"""
        # 检查密码是否有效（非空字符串）
        has_valid_password = bool(self.password and self.password.strip())
        has_private_key = bool(self.private_key_path)

        # 如果明确指定 auth_method，使用指定的方法
        if self.auth_method == "private_key":
            if not has_private_key and not has_valid_password:
                raise ValueError(
                    "Private key authentication requires either private_key_path or password as fallback"
                )
        elif self.auth_method == "password":
            if not has_valid_password:
                raise ValueError(
                    "Password authentication requires a valid password (non-empty string)"
                )
        # 如果未指定 auth_method，根据提供的凭证自动选择
        elif not self.auth_method:
            if has_private_key:
                self.auth_method = "private_key"
            elif has_valid_password:
                self.auth_method = "password"
            else:
                raise ValueError(
                    "Must provide either private_key_path or password for authentication"
                )

        return self

    def get_retry_config(self) -> RetryConfig:
        """获取重试配置"""
        return self.retry_config or RetryConfig()
