from __future__ import annotations

import asyncio
import threading
from typing import Optional, Protocol, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .connection_config import ConnectionConfig
from .exceptions import ConnectionException, AuthenticationException, CommandExecutionException
from .logging_config import get_logger
from .executor import get_executor


class ClientType(Enum):
    ASYNCSSH = "asyncssh"
    PARAMIKO = "paramiko"


class HealthCheckStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    status: HealthCheckStatus
    latency_ms: float = 0.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class ConnectionInfo:
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
    async def connect(self, config: ConnectionConfig) -> ConnectionInfo: ...
    async def disconnect(self, session_id: str) -> None: ...
    async def execute_command(self, session_id: str, command: str, timeout: int = 30) -> dict: ...
    async def health_check(self, session_id: str) -> HealthCheckResult: ...


class SSHService:
    """
    SSH 服务层 - 业务逻辑核心
    
    职责：
    1. 统一的连接管理
    2. 会话生命周期管理
    3. 健康检查与监控
    4. 异常处理与重试
    5. 日志记录
    
    改进特性：
    - 线程安全的数据访问
    - 异步执行阻塞操作
    - 超时控制
    - 连接池管理
    """
    
    def __init__(self):
        self._logger = get_logger("SSHService")
        self._sessions: dict[str, ConnectionInfo] = {}
        self._clients: dict[str, Any] = {}
        self._client_factory = None
        self._lock = threading.RLock()
        self._executor = get_executor()
    
    def set_client_factory(self, factory) -> None:
        """设置客户端工厂"""
        with self._lock:
            self._client_factory = factory
    
    async def connect(
        self, 
        config: ConnectionConfig, 
        client_type: Optional[ClientType] = None
    ) -> ConnectionInfo:
        """
        建立 SSH 连接（异步版本）
        
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
            # 使用线程池执行阻塞的连接操作
            client = await self._executor.submit(
                self._create_client_sync, config, client_type,
                timeout=config.timeout + 10
            )
            
            connection_result = await self._executor.submit(
                client.connect, timeout=config.timeout
            )
            
            if not connection_result.success:
                raise ConnectionException(connection_result.message)
            
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
            
            with self._lock:
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
    
    async def disconnect(self, session_id: str) -> None:
        """断开 SSH 连接（异步版本）"""
        with self._lock:
            if session_id not in self._sessions:
                self._logger.warning(f"Session not found: {session_id}")
                return
        
        client = None
        with self._lock:
            client = self._clients.pop(session_id, None)
        
        if client:
            try:
                await self._executor.submit(client.close)
                self._logger.info(f"Disconnected: session_id={session_id}")
            except Exception as e:
                self._logger.error(f"Error closing connection: {str(e)}")
        
        with self._lock:
            self._sessions.pop(session_id, None)
    
    async def execute_command(
        self, 
        session_id: str, 
        command: str, 
        timeout: int = 30
    ) -> dict:
        """
        执行命令（异步版本）
        
        Args:
            session_id: 会话 ID
            command: 要执行的命令
            timeout: 超时时间（秒）
            
        Returns:
            dict: 命令执行结果
        """
        with self._lock:
            if session_id not in self._sessions:
                raise ConnectionException(f"Session not found: {session_id}")
            
            connection_info = self._sessions[session_id]
            client = self._clients.get(session_id)
        
        if not client or not getattr(client, 'is_connected', False):
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].is_connected = False
            raise ConnectionException(f"Session disconnected: {session_id}")
        
        self._logger.debug(f"Executing command: {command}")
        
        try:
            result = await self._executor.submit(
                client.execute_command, command, timeout=timeout
            )
            
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].last_activity = datetime.now()
                    self._sessions[session_id].command_count += 1
            
            return {
                "success": result.return_code == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
                "session_id": session_id
            }
            
        except asyncio.TimeoutError:
            raise CommandExecutionException(
                f"Command execution timed out after {timeout}s",
                command=command
            )
        except Exception as e:
            self._logger.error(f"Command execution failed: {str(e)}")
            raise CommandExecutionException(
                f"Failed to execute command: {str(e)}",
                command=command,
                original_error=e
            )
    
    async def health_check(self, session_id: str) -> HealthCheckResult:
        """
        健康检查（异步版本）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            HealthCheckResult: 健康检查结果
        """
        with self._lock:
            if session_id not in self._sessions:
                return HealthCheckResult(
                    status=HealthCheckStatus.UNKNOWN,
                    message=f"Session not found: {session_id}"
                )
            
            connection_info = self._sessions[session_id]
            client = self._clients.get(session_id)
        
        if not client:
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].is_connected = False
            return HealthCheckResult(
                status=HealthCheckStatus.UNHEALTHY,
                message="Client not available"
            )
        
        try:
            start_time = datetime.now()
            
            result = await self._executor.submit(
                client.execute_command, "echo 'health_check'", timeout=5
            )
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            is_healthy = result.return_code == 0
            
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].is_connected = is_healthy
            
            return HealthCheckResult(
                status=HealthCheckStatus.HEALTHY if is_healthy else HealthCheckStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="OK" if is_healthy else f"Command failed: {result.stderr}"
            )
            
        except Exception as e:
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].is_connected = False
            return HealthCheckResult(
                status=HealthCheckStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )
    
    def get_session_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """获取会话信息（线程安全）"""
        with self._lock:
            return self._sessions.get(session_id)
    
    def list_sessions(self) -> list[ConnectionInfo]:
        """列出所有会话（线程安全）"""
        with self._lock:
            return list(self._sessions.values())
    
    def get_active_session_count(self) -> int:
        """获取活跃会话数（线程安全）"""
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_connected)
    
    async def disconnect_all(self) -> None:
        """断开所有会话（异步版本）"""
        session_ids = []
        with self._lock:
            session_ids = list(self._sessions.keys())
        
        disconnect_tasks = [self.disconnect(session_id) for session_id in session_ids]
        await asyncio.gather(*disconnect_tasks)
    
    def _create_client_sync(self, config: ConnectionConfig, client_type: Optional[ClientType] = None):
        """创建 SSH 客户端（同步方法）"""
        from .clients.factory import SSHClientFactory
        from .clients.interface import ClientType as InterfaceClientType
        
        interface_client_type = None
        if client_type:
            interface_client_type = InterfaceClientType(client_type.value)
        
        return SSHClientFactory.create(config, interface_client_type)


_ssh_service_instance: Optional[SSHService] = None
_ssh_service_lock = threading.Lock()


def get_ssh_service() -> SSHService:
    """获取 SSH 服务单例（线程安全）"""
    global _ssh_service_instance
    with _ssh_service_lock:
        if _ssh_service_instance is None:
            _ssh_service_instance = SSHService()
    return _ssh_service_instance