from __future__ import annotations

from typing import Optional, Dict, Any
from pathlib import Path
import json

from ..connection_config import ConnectionConfig
from .interface import SSHClientInterface, ClientType
from .paramiko_client import ParamikoClient


class SSHClientFactory:
    """SSH 客户端工厂类"""
    
    _client_classes: Dict[ClientType, type] = {}
    _default_client_type: ClientType = ClientType.PARAMIKO
    
    @classmethod
    def register(cls, client_type: ClientType, client_class: type):
        """注册 SSH 客户端实现"""
        cls._client_classes[client_type] = client_class
    
    @classmethod
    def set_default(cls, client_type: ClientType):
        """设置默认客户端类型"""
        cls._default_client_type = client_type
    
    @classmethod
    def create(cls, config: ConnectionConfig, client_type: Optional[ClientType] = None) -> SSHClientInterface:
        """创建 SSH 客户端实例"""
        if client_type is None:
            client_type = cls._default_client_type
        
        if client_type not in cls._client_classes:
            raise ValueError(f"Unsupported client type: {client_type}")
        
        client_class = cls._client_classes[client_type]
        return client_class(config)
    
    @classmethod
    def get_available_types(cls) -> list[ClientType]:
        """获取可用的客户端类型"""
        return list(cls._client_classes.keys())


# 默认注册 Paramiko 客户端
SSHClientFactory.register(ClientType.PARAMIKO, ParamikoClient)

# 尝试注册其他客户端（如果已安装）
try:
    from .additional_clients import FabricClient
    SSHClientFactory.register(ClientType.FABRIC, FabricClient)
except ImportError:
    pass

try:
    from .additional_clients import AsyncSSHClient
    SSHClientFactory.register(ClientType.ASYNCSSH, AsyncSSHClient)
except ImportError:
    pass

try:
    from .additional_clients import SSH2Client
    SSHClientFactory.register(ClientType.SSH2, SSH2Client)
except ImportError:
    pass


class ClientConfig:
    """SSH 客户端配置管理"""
    
    DEFAULT_CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "client_config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """加载配置"""
        if not self.config_path.exists():
            self._config = self._get_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception:
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "default_client": "paramiko",
            "clients": {
                "paramiko": {
                    "enabled": True,
                    "timeout": 30,
                    "keepalive_interval": 30,
                    "session_timeout": 7200
                }
            }
        }
    
    def get_default_client_type(self) -> ClientType:
        """获取默认客户端类型"""
        default = self._config.get("default_client", "paramiko")
        try:
            return ClientType(default)
        except ValueError:
            return ClientType.PARAMIKO
    
    def get_client_config(self, client_type: ClientType) -> Dict[str, Any]:
        """获取指定客户端的配置"""
        clients = self._config.get("clients", {})
        return clients.get(client_type.value, {})
    
    def is_client_enabled(self, client_type: ClientType) -> bool:
        """检查客户端是否启用"""
        config = self.get_client_config(client_type)
        return config.get("enabled", True)
    
    def set_default_client(self, client_type: ClientType) -> None:
        """设置默认客户端"""
        self._config["default_client"] = client_type.value
        SSHClientFactory.set_default(client_type)
    
    def save(self) -> None:
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2)
    
    @classmethod
    def get_default(cls) -> ClientConfig:
        """获取默认配置实例"""
        return cls()


# 全局配置实例
_default_client_config: Optional[ClientConfig] = None


def get_client_config() -> ClientConfig:
    """获取全局客户端配置"""
    global _default_client_config
    if _default_client_config is None:
        _default_client_config = ClientConfig.get_default()
        # 设置默认客户端
        SSHClientFactory.set_default(_default_client_config.get_default_client_type())
    return _default_client_config
