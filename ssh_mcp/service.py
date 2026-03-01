from __future__ import annotations

from typing import Optional, Protocol, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .connection_config import ConnectionConfig
from .exceptions import ConnectionException, AuthenticationException, CommandExecutionException
from .logging_config import get_logger


class ClientType(Enum):
    """支持的 SSH 客户端类型"""
    PARAMIKO = "paramiko"
    FABRIC = "fabric"
    ASYNCSSH = "asyncssh"
    SSH2 = "ssh2"
    SYSTEM = "system"


class HealthCheckStatus(Enum):
    """健康检查状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthCheckStatus
    latency_ms: float = 0.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class ConnectionInfo:
    """连接信息"""
    session_id: str
    host: str
    port: int
    username: str
    client_type: ClientType
    connected_at: datetime
    last_activity: datetime
    is_connected: bool
    command_count: int = 0


class SSHServiceProtocol(Protocol):
    """SSH 服务协议定义"""
    
    def connect(self, config: ConnectionConfig) -> ConnectionInfo: ...
    def disconnect(self, session_id: str) -> None: ...
    def execute_command(self, session_id: str, command: str, timeout: int = 30) -> dict: ...
    def health_check(self, session_id: str) -> HealthCheckResult: ...


class SSHService:
    """
    SSH 服务层 - 业务逻辑核心
    
    职责：
    1. 统一的连接管理
    2. 会话生命周期管理
    3. 健康检查与监控
    4. 异常处理与重试
    5. 日志记录
    """
    
    def __init__(self):
        self._logger = get_logger("SSHService")
        self._sessions: dict[str, ConnectionInfo] = {}
        self._clients: dict[str, Any] = {}
        self._client_factory = None
    
    def set_client_factory(self, factory) -> None:
        """设置客户端工厂"""
        self._client_factory = factory
    
    def connect(
        self, 
        config: ConnectionConfig, 
        client_type: Optional[ClientType] = None
    ) -> ConnectionInfo:
        """
        建立 SSH 连接
        
        Args:
            config: 连接配置
            client_type: 客户端类型（可选，默认使用配置的客户端）
            
        Returns:
            ConnectionInfo: 连接信息
            
        Raises:
            ConnectionException: 连接失败
            AuthenticationException: 认证失败
        """
        session_id = str(uuid.uuid4())
        
        self._logger.info(
            f"Connecting to {config.host}:{config.port} as {config.username} "
            f"(client: {client_type or 'default'})"
        )
        
        try:
            client = self._create_client(config, client_type)
            client.connect(timeout=config.timeout)
            
            connection_info = ConnectionInfo(
                session_id=session_id,
                host=config.host,
                port=config.port,
                username=config.username,
                client_type=client_type or ClientType.PARAMIKO,
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                is_connected=True,
                command_count=0
            )
            
            self._sessions[session_id] = connection_info
            self._clients[session_id] = client
            
            self._logger.info(f"Successfully connected: session_id={session_id}")
            
            return connection_info
            
        except Exception as e:
            self._logger.error(f"Connection failed: {str(e)}")
            if "authentication" in str(e).lower() or "auth" in str(e).lower():
                raise AuthenticationException(
                    f"Authentication failed for {config.username}@{config.host}",
                    original_error=e
                )
            raise ConnectionException(
                f"Failed to connect to {config.host}:{config.port}",
                original_error=e
            )
    
    def disconnect(self, session_id: str) -> None:
        """断开 SSH 连接"""
        if session_id not in self._sessions:
            self._logger.warning(f"Session not found: {session_id}")
            return
        
        client = self._clients.pop(session_id, None)
        if client:
            try:
                client.close()
                self._logger.info(f"Disconnected: session_id={session_id}")
            except Exception as e:
                self._logger.error(f"Error closing connection: {str(e)}")
        
        self._sessions.pop(session_id, None)
    
    def execute_command(
        self, 
        session_id: str, 
        command: str, 
        timeout: int = 30
    ) -> dict:
        """
        执行命令
        
        Args:
            session_id: 会话 ID
            command: 要执行的命令
            timeout: 超时时间（秒）
            
        Returns:
            dict: 命令执行结果
        """
        if session_id not in self._sessions:
            raise ConnectionException(f"Session not found: {session_id}")
        
        connection_info = self._sessions[session_id]
        client = self._clients.get(session_id)
        
        if not client or not getattr(client, 'is_connected', False):
            connection_info.is_connected = False
            raise ConnectionException(f"Session disconnected: {session_id}")
        
        self._logger.debug(f"Executing command: {command}")
        
        try:
            result = client.execute_command(command, timeout=timeout)
            
            connection_info.last_activity = datetime.now()
            connection_info.command_count += 1
            
            return {
                "success": result.return_code == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
                "session_id": session_id
            }
            
        except Exception as e:
            self._logger.error(f"Command execution failed: {str(e)}")
            raise CommandExecutionException(
                f"Failed to execute command: {str(e)}",
                command=command,
                original_error=e
            )
    
    def health_check(self, session_id: str) -> HealthCheckResult:
        """
        健康检查
        
        Args:
            session_id: 会话 ID
            
        Returns:
            HealthCheckResult: 健康检查结果
        """
        if session_id not in self._sessions:
            return HealthCheckResult(
                status=HealthCheckStatus.UNKNOWN,
                message=f"Session not found: {session_id}"
            )
        
        connection_info = self._sessions[session_id]
        client = self._clients.get(session_id)
        
        if not client:
            connection_info.is_connected = False
            return HealthCheckResult(
                status=HealthCheckStatus.UNHEALTHY,
                message="Client not available"
            )
        
        try:
            import time
            start_time = time.time()
            
            result = client.execute_command("echo 'health_check'", timeout=5)
            
            latency_ms = (time.time() - start_time) * 1000
            
            is_healthy = result.return_code == 0
            
            connection_info.is_connected = is_healthy
            
            return HealthCheckResult(
                status=HealthCheckStatus.HEALTHY if is_healthy else HealthCheckStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="OK" if is_healthy else f"Command failed: {result.stderr}"
            )
            
        except Exception as e:
            connection_info.is_connected = False
            return HealthCheckResult(
                status=HealthCheckStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )
    
    def get_session_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """获取会话信息"""
        return self._sessions.get(session_id)
    
    def list_sessions(self) -> list[ConnectionInfo]:
        """列出所有会话"""
        return list(self._sessions.values())
    
    def get_active_session_count(self) -> int:
        """获取活跃会话数"""
        return sum(1 for s in self._sessions.values() if s.is_connected)
    
    def disconnect_all(self) -> None:
        """断开所有会话"""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            self.disconnect(session_id)
    
    def _create_client(self, config: ConnectionConfig, client_type: Optional[ClientType] = None):
        """创建 SSH 客户端"""
        from .clients.factory import SSHClientFactory
        from .clients.interface import ClientType as InterfaceClientType
        
        interface_client_type = None
        if client_type:
            interface_client_type = InterfaceClientType(client_type.value)
        
        return SSHClientFactory.create(config, interface_client_type)


_ssh_service_instance: Optional[SSHService] = None


def get_ssh_service() -> SSHService:
    """获取 SSH 服务单例"""
    global _ssh_service_instance
    if _ssh_service_instance is None:
        _ssh_service_instance = SSHService()
    return _ssh_service_instance
