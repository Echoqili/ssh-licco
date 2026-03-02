from __future__ import annotations

import asyncio
import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
import uuid

from .connection_config import ConnectionConfig
from .clients.interface import SSHClientInterface, ClientType
from .clients.factory import SSHClientFactory
from .exceptions import ConnectionException, PoolExhaustedException
from .logging_config import get_logger


class PooledConnectionState(Enum):
    """连接池连接状态"""
    IDLE = "idle"
    IN_USE = "in_use"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class PooledConnection:
    """池化连接"""
    connection_id: str
    client: SSHClientInterface
    config: ConnectionConfig
    client_type: ClientType
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    state: PooledConnectionState = PooledConnectionState.IDLE
    error_count: int = 0
    
    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used = datetime.now()
        self.use_count += 1
        self.state = PooledConnectionState.IN_USE
    
    def mark_idle(self) -> None:
        """标记为空闲"""
        self.state = PooledConnectionState.IDLE
    
    def mark_error(self) -> None:
        """标记为错误"""
        self.error_count += 1
        self.state = PooledConnectionState.ERROR
    
    def is_healthy(self, max_error_count: int = 3) -> bool:
        """检查连接是否健康"""
        if self.state == PooledConnectionState.CLOSED:
            return False
        if self.error_count >= max_error_count:
            return False
        if not self.client.is_connected:
            return False
        return True


@dataclass
class PoolConfig:
    """连接池配置"""
    min_size: int = 1
    max_size: int = 10
    max_idle_time: int = 300
    max_use_count: int = 100
    max_error_count: int = 3
    acquire_timeout: int = 30
    validation_interval: int = 60
    enable_auto_recycle: bool = True


class ConnectionPool:
    """
    SSH 连接池 - 高性能连接管理
    
    特性：
    - 连接复用，减少连接开销
    - 连接健康检查与自动回收
    - 线程安全
    - 支持连接预热
    """
    
    def __init__(
        self, 
        config: ConnectionConfig,
        pool_config: Optional[PoolConfig] = None,
        client_type: Optional[ClientType] = None
    ):
        self._config = config
        self._pool_config = pool_config or PoolConfig()
        self._client_type = client_type or ClientType.ASYNCSSH
        
        self._logger = get_logger(f"ConnectionPool.{config.host}")
        
        self._pool: Dict[str, PooledConnection] = {}
        self._available: Queue = Queue()
        self._lock = threading.RLock()
        
        self._closed = False
        self._init_count = 0
        
        self._validation_task: Optional[threading.Thread] = None
        if self._pool_config.enable_auto_recycle:
            self._start_validation()
    
    def _create_client(self) -> SSHClientInterface:
        """创建新的SSH客户端"""
        return SSHClientFactory.create(
            self._client_type,
            self._config
        )
    
    def _create_and_connect(self) -> PooledConnection:
        """创建并连接SSH客户端"""
        client = self._create_client()
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = client.connect(timeout=self._config.timeout)
                if result.success:
                    connection_id = str(uuid.uuid4())
                    pooled = PooledConnection(
                        connection_id=connection_id,
                        client=client,
                        config=self._config,
                        client_type=self._client_type
                    )
                    self._logger.info(
                        f"Created new connection: {connection_id} "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    return pooled
                last_error = result.message
            except Exception as e:
                last_error = str(e)
                self._logger.warning(
                    f"Connection attempt {attempt + 1} failed: {last_error}"
                )
                time.sleep(0.5 * (attempt + 1))
        
        raise ConnectionException(
            f"Failed to create connection after {max_retries} attempts: {last_error}"
        )
    
    def initialize(self) -> None:
        """初始化连接池，创建最小连接数"""
        if self._init_count > 0:
            return
        
        with self._lock:
            if self._init_count > 0:
                return
            
            self._logger.info(
                f"Initializing connection pool with {self._pool_config.min_size} connections"
            )
            
            for i in range(self._pool_config.min_size):
                try:
                    pooled = self._create_and_connect()
                    self._pool[pooled.connection_id] = pooled
                    self._available.put(pooled)
                    self._init_count += 1
                except Exception as e:
                    self._logger.error(f"Failed to create initial connection: {e}")
            
            self._logger.info(
                f"Connection pool initialized: {self._init_count} connections"
            )
    
    def acquire(self, timeout: Optional[int] = None) -> PooledConnection:
        """
        获取一个连接
        
        Args:
            timeout: 获取超时时间（秒），默认使用池配置
            
        Returns:
            PooledConnection: 池化连接
            
        Raises:
            PoolExhaustedException: 连接池耗尽
            ConnectionException: 获取连接失败
        """
        if self._closed:
            raise ConnectionException("Connection pool is closed")
        
        timeout = timeout or self._pool_config.acquire_timeout
        start_time = time.time()
        
        while True:
            try:
                pooled = self._available.get(timeout=1)
                
                if not pooled.is_healthy(max_error_count=self._pool_config.max_error_count):
                    self._remove_connection(pooled.connection_id)
                    continue
                
                pooled.mark_used()
                self._logger.debug(
                    f"Acquired connection: {pooled.connection_id} "
                    f"(total: {len(self._pool)}, available: {self._available.qsize()})"
                )
                return pooled
                
            except Empty:
                with self._lock:
                    if len(self._pool) < self._pool_config.max_size:
                        pooled = self._create_and_connect()
                        self._pool[pooled.connection_id] = pooled
                        pooled.mark_used()
                        return pooled
                
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise PoolExhaustedException(
                        f"Connection pool exhausted, timeout after {timeout}s"
                    )
                
                self._logger.warning(
                    f"Waiting for available connection, "
                    f"elapsed: {elapsed:.1f}s, pool size: {len(self._pool)}"
                )
    
    def release(self, pooled: PooledConnection, force_close: bool = False) -> None:
        """
        释放连接回连接池
        
        Args:
            pooled: 池化连接
            force_close: 是否强制关闭连接
        """
        if self._closed:
            self._close_connection(pooled)
            return
        
        if force_close:
            self._remove_connection(pooled.connection_id)
            return
        
        if not pooled.is_healthy(max_error_count=self._pool_config.max_error_count):
            self._remove_connection(pooled.connection_id)
            return
        
        if pooled.use_count >= self._pool_config.max_use_count:
            self._logger.info(
                f"Connection {pooled.connection_id} exceeded max use count, closing"
            )
            self._remove_connection(pooled.connection_id)
            return
        
        pooled.mark_idle()
        self._available.put(pooled)
        
        self._logger.debug(
            f"Released connection: {pooled.connection_id} "
            f"(total: {len(self._pool)}, available: {self._available.qsize()})"
        )
    
    def _remove_connection(self, connection_id: str) -> None:
        """移除连接"""
        with self._lock:
            pooled = self._pool.pop(connection_id, None)
            if pooled:
                self._close_connection(pooled)
    
    def _close_connection(self, pooled: PooledConnection) -> None:
        """关闭连接"""
        try:
            pooled.client.close()
            pooled.state = PooledConnectionState.CLOSED
            self._logger.debug(f"Closed connection: {pooled.connection_id}")
        except Exception as e:
            self._logger.warning(f"Error closing connection: {e}")
    
    def _start_validation(self) -> None:
        """启动连接验证任务"""
        self._validation_task = threading.Thread(
            target=self._validation_loop,
            daemon=True
        )
        self._validation_task.start()
    
    def _validation_loop(self) -> None:
        """连接验证循环"""
        while not self._closed:
            time.sleep(self._pool_config.validation_interval)
            
            if self._closed:
                break
            
            self._validate_connections()
    
    def _validate_connections(self) -> None:
        """验证所有连接"""
        connections_to_close = []
        
        with self._lock:
            for connection_id, pooled in self._pool.items():
                if pooled.state == PooledConnectionState.IN_USE:
                    continue
                
                idle_time = (datetime.now() - pooled.last_used).total_seconds()
                if idle_time > self._pool_config.max_idle_time:
                    connections_to_close.append(connection_id)
                    continue
                
                if not pooled.client.is_connected:
                    connections_to_close.append(connection_id)
        
        for connection_id in connections_to_close:
            self._remove_connection(connection_id)
            self._logger.info(
                f"Closed idle connection: {connection_id}, "
                f"pool size: {len(self._pool)}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            total = len(self._pool)
            available = self._available.qsize()
            in_use = total - available
            
            return {
                "total": total,
                "available": available,
                "in_use": in_use,
                "config": {
                    "min_size": self._pool_config.min_size,
                    "max_size": self._pool_config.max_size,
                    "max_idle_time": self._pool_config.max_idle_time,
                    "max_use_count": self._pool_config.max_use_count
                }
            }
    
    def close(self) -> None:
        """关闭连接池"""
        self._closed = True
        
        with self._lock:
            for pooled in list(self._pool.values()):
                self._close_connection(pooled)
            
            self._pool.clear()
            while not self._available.empty():
                try:
                    self._available.get_nowait()
                except Empty:
                    break
        
        self._logger.info("Connection pool closed")


class PooledSSHClient:
    """
    池化SSH客户端 - 包装连接池提供会话接口
    
    用法:
        pool = ConnectionPool(config)
        client = PooledSSHClient(pool)
        try:
            result = client.execute_command("ls -la")
        finally:
            client.close()
    """
    
    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._pooled_connection: Optional[PooledConnection] = None
        self._closed = False
    
    def __enter__(self) -> "PooledSSHClient":
        self._pooled_connection = self._pool.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
    
    @property
    def client(self) -> SSHClientInterface:
        """获取底层SSH客户端"""
        if not self._pooled_connection:
            raise ConnectionException("Not acquired connection from pool")
        return self._pooled_connection.client
    
    @property
    def connection_id(self) -> str:
        """获取连接ID"""
        if not self._pooled_connection:
            raise ConnectionException("Not acquired connection from pool")
        return self._pooled_connection.connection_id
    
    def execute_command(self, command: str, timeout: int = 30) -> Any:
        """执行命令"""
        return self.client.execute_command(command, timeout)
    
    def execute_command_stream(self, command: str) -> Any:
        """流式执行命令"""
        return self.client.execute_command_stream(command)
    
    def upload_file(self, local_path: str, remote_path: str) -> Any:
        """上传文件"""
        return self.client.upload_file(local_path, remote_path)
    
    def download_file(self, remote_path: str, local_path: str) -> Any:
        """下载文件"""
        return self.client.download_file(remote_path, local_path)
    
    def list_directory(self, remote_path: str = ".") -> Any:
        """列出目录"""
        return self.client.list_directory(remote_path)
    
    def close(self) -> None:
        """释放连接回连接池"""
        if self._pooled_connection and not self._closed:
            self._pooled_connection.mark_used()
            self._pool.release(self._pooled_connection)
            self._pooled_connection = None
            self._closed = True
