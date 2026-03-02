from __future__ import annotations

import asyncio
import time
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .connection_config import ConnectionConfig
from .clients.interface import ClientType, CommandResult
from .clients.factory import SSHClientFactory
from .connection_pool import ConnectionPool, PoolConfig, PooledSSHClient
from .exceptions import ConnectionException, CommandExecutionException
from .logging_config import get_logger


class BatchResultStatus(Enum):
    """批量执行结果状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class HostResult:
    """单主机执行结果"""
    host: str
    port: int
    username: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    error_message: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BatchExecutionResult:
    """批量执行结果"""
    batch_id: str
    status: BatchResultStatus
    total_hosts: int
    success_count: int = 0
    failed_count: int = 0
    results: List[HostResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class BatchExecutor:
    """
    批量执行器 - 多主机并行命令执行
    
    特性：
    - 多主机并行执行
    - 失败隔离，单主机异常不影响其他主机
    - 连接池复用
    - 超时控制
    - 进度回调
    """
    
    def __init__(
        self,
        hosts: List[ConnectionConfig],
        client_type: Optional[ClientType] = None,
        pool_config: Optional[PoolConfig] = None,
        max_workers: int = 10,
        timeout: int = 60
    ):
        self._hosts = hosts
        self._client_type = client_type or ClientType.ASYNCSSH
        self._pool_config = pool_config
        self._max_workers = max_workers
        self._timeout = timeout
        
        self._logger = get_logger("BatchExecutor")
        
        self._pools: Dict[str, ConnectionPool] = {}
    
    def _get_pool(self, host_config: ConnectionConfig) -> ConnectionPool:
        """获取或创建连接池"""
        key = f"{host_config.host}:{host_config.port}"
        
        if key not in self._pools:
            pool = ConnectionPool(
                config=host_config,
                pool_config=self._pool_config,
                client_type=self._client_type
            )
            pool.initialize()
            self._pools[key] = pool
        
        return self._pools[key]
    
    def _execute_on_host(
        self, 
        host_config: ConnectionConfig, 
        command: str
    ) -> HostResult:
        """在单个主机上执行命令"""
        start_time = time.time()
        
        result = HostResult(
            host=host_config.host,
            port=host_config.port,
            username=host_config.username,
            success=False
        )
        
        try:
            pool = self._get_pool(host_config)
            
            with PooledSSHClient(pool) as client:
                cmd_result = client.execute_command(command, timeout=self._timeout)
                
                result.stdout = cmd_result.stdout
                result.stderr = cmd_result.stderr
                result.return_code = cmd_result.return_code
                result.success = cmd_result.return_code == 0
                
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.return_code = -1
        
        result.latency_ms = (time.time() - start_time) * 1000
        
        return result
    
    def execute(
        self, 
        command: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchExecutionResult:
        """
        批量执行命令
        
        Args:
            command: 要执行的命令
            progress_callback: 进度回调 (completed, total)
            
        Returns:
            BatchExecutionResult: 批量执行结果
        """
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        
        self._logger.info(
            f"Starting batch execution: batch_id={batch_id}, "
            f"hosts={len(self._hosts)}, command='{command}'"
        )
        
        results: List[HostResult] = []
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(self._hosts))
        ) as executor:
            future_to_host = {
                executor.submit(
                    self._execute_on_host, 
                    host_config, 
                    command
                ): host_config
                for host_config in self._hosts
            }
            
            for future in concurrent.futures.as_completed(future_to_host):
                host_config = future_to_host[future]
                
                try:
                    result = future.result(timeout=self._timeout + 10)
                    results.append(result)
                    
                    if result.success:
                        self._logger.debug(
                            f"Host {host_config.host} succeeded "
                            f"(latency: {result.latency_ms:.2f}ms)"
                        )
                    else:
                        self._logger.warning(
                            f"Host {host_config.host} failed: {result.error_message}"
                        )
                        
                except concurrent.futures.TimeoutError:
                    error_result = HostResult(
                        host=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        success=False,
                        error_message=f"Command timeout after {self._timeout}s",
                        return_code=-1
                    )
                    results.append(error_result)
                    self._logger.error(
                        f"Host {host_config.host} timeout"
                    )
                    
                except Exception as e:
                    error_result = HostResult(
                        host=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        success=False,
                        error_message=str(e),
                        return_code=-1
                    )
                    results.append(error_result)
                    self._logger.error(
                        f"Host {host_config.host} error: {str(e)}"
                    )
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(self._hosts))
        
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        
        if failed_count == 0:
            status = BatchResultStatus.SUCCESS
        elif success_count == 0:
            status = BatchResultStatus.FAILED
        else:
            status = BatchResultStatus.PARTIAL
        
        total_time_ms = (time.time() - start_time) * 1000
        
        self._logger.info(
            f"Batch execution completed: batch_id={batch_id}, "
            f"success={success_count}, failed={failed_count}, "
            f"total_time={total_time_ms:.2f}ms"
        )
        
        return BatchExecutionResult(
            batch_id=batch_id,
            status=status,
            total_hosts=len(self._hosts),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            total_time_ms=total_time_ms
        )
    
    async def execute_async(
        self, 
        command: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchExecutionResult:
        """
        异步批量执行命令
        
        Args:
            command: 要执行的命令
            progress_callback: 进度回调 (completed, total)
            
        Returns:
            BatchExecutionResult: 批量执行结果
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            None,
            self.execute,
            command,
            progress_callback
        )
    
    def close(self) -> None:
        """关闭所有连接池"""
        for pool in self._pools.values():
            pool.close()
        
        self._pools.clear()
        
        self._logger.info("BatchExecutor closed")


class AsyncBatchExecutor:
    """
    异步批量执行器 - 使用asyncssh实现高性能并发
    
    特性：
    - 原生异步支持
    - 高并发性能
    - 事件循环管理
    """
    
    def __init__(
        self,
        hosts: List[ConnectionConfig],
        client_type: Optional[ClientType] = None,
        max_concurrent: int = 50,
        timeout: int = 60
    ):
        self._hosts = hosts
        self._client_type = client_type or ClientType.ASYNCSSH
        self._max_concurrent = max_concurrent
        self._timeout = timeout
        
        self._logger = get_logger("AsyncBatchExecutor")
    
    async def _execute_single(
        self, 
        host_config: ConnectionConfig, 
        command: str,
        semaphore: asyncio.Semaphore
    ) -> HostResult:
        """异步执行单个主机命令"""
        async with semaphore:
            start_time = time.time()
            
            result = HostResult(
                host=host_config.host,
                port=host_config.port,
                username=host_config.username,
                success=False
            )
            
            try:
                import asyncssh
                
                async with asyncssh.connect(
                    host=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password,
                    client_keys=(
                        [str(host_config.private_key_path)] 
                        if host_config.private_key_path else None
                    ),
                    passphrase=host_config.passphrase,
                    timeout=self._timeout
                ) as conn:
                    result_obj = await conn.run(command, timeout=self._timeout)
                    
                    result.stdout = result_obj.stdout
                    result.stderr = result_obj.stderr
                    result.return_code = result_obj.exit_status
                    result.success = result_obj.exit_status == 0
                    
            except asyncio.TimeoutError:
                result.success = False
                result.error_message = f"Command timeout after {self._timeout}s"
                
            except Exception as e:
                result.success = False
                result.error_message = str(e)
            
            result.latency_ms = (time.time() - start_time) * 1000
            
            return result
    
    async def execute(
        self, 
        command: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchExecutionResult:
        """
        异步批量执行命令
        
        Args:
            command: 要执行的命令
            progress_callback: 进度回调 (completed, total)
            
        Returns:
            BatchExecutionResult: 批量执行结果
        """
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        
        self._logger.info(
            f"Starting async batch execution: batch_id={batch_id}, "
            f"hosts={len(self._hosts)}, command='{command}'"
        )
        
        semaphore = asyncio.Semaphore(self._max_concurrent)
        
        tasks = [
            self._execute_single(host_config, command, semaphore)
            for host_config in self._hosts
        ]
        
        results: List[HostResult] = []
        
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(self._hosts))
        
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        
        if failed_count == 0:
            status = BatchResultStatus.SUCCESS
        elif success_count == 0:
            status = BatchResultStatus.FAILED
        else:
            status = BatchResultStatus.PARTIAL
        
        total_time_ms = (time.time() - start_time) * 1000
        
        self._logger.info(
            f"Async batch execution completed: batch_id={batch_id}, "
            f"success={success_count}, failed={failed_count}, "
            f"total_time={total_time_ms:.2f}ms"
        )
        
        return BatchExecutionResult(
            batch_id=batch_id,
            status=status,
            total_hosts=len(self._hosts),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            total_time_ms=total_time_ms
        )
