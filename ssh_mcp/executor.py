from __future__ import annotations

import asyncio
import concurrent.futures
import os
import threading
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar


def _default_max_workers() -> int:
    """获取默认最大工作线程数（限制上限防止资源耗尽）"""
    cpu_count = os.cpu_count() or 4
    # 限制最大线程数：CPU * 5，上限 20
    return min(cpu_count * 5, 20)


T = TypeVar("T")


class ThreadPoolExecutor:
    """
    线程池执行器 - 支持异步执行阻塞操作

    特性：
    - 自动管理线程池生命周期
    - 支持超时控制
    - 提供装饰器简化异步调用
    - 线程安全的任务管理
    """

    _instance: ThreadPoolExecutor | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_workers: int | None = None):
        if hasattr(self, "_initialized"):
            return

        self._max_workers = max_workers or (_default_max_workers())
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._executor_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._initialized = True

    @property
    def executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """获取线程池执行器（懒加载）"""
        if self._shutdown_event.is_set():
            raise RuntimeError("Executor has been shutdown")

        with self._executor_lock:
            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=self._max_workers, thread_name_prefix="ssh-mcp-exec-"
                )
        return self._executor

    async def submit(
        self, func: Callable[..., T], *args: Any, timeout: int | None = None, **kwargs: Any
    ) -> T:
        """
        异步提交任务到线程池执行

        Args:
            func: 要执行的函数
            *args: 位置参数
            timeout: 超时时间（秒），None表示不限制
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            asyncio.TimeoutError: 超时异常
            Exception: 函数执行异常
        """
        loop = asyncio.get_event_loop()

        def task_wrapper():
            return func(*args, **kwargs)

        try:
            if timeout is not None:
                return await asyncio.wait_for(
                    loop.run_in_executor(self.executor, task_wrapper), timeout=timeout
                )
            else:
                return await loop.run_in_executor(self.executor, task_wrapper)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"Task execution timed out after {timeout}s")

    async def map(
        self, func: Callable[..., T], *iterables: Any, timeout: int | None = None
    ) -> list[T]:
        """
        并行执行多个任务

        Args:
            func: 要执行的函数
            *iterables: 可迭代参数
            timeout: 总超时时间（秒）

        Returns:
            结果列表
        """
        loop = asyncio.get_event_loop()
        futures = []

        for args in zip(*iterables):
            futures.append(loop.run_in_executor(self.executor, func, *args))

        if timeout is not None:
            return await asyncio.wait_for(asyncio.gather(*futures), timeout=timeout)
        else:
            return await asyncio.gather(*futures)

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池"""
        self._shutdown_event.set()
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def running(self) -> bool:
        """检查执行器是否正在运行"""
        return not self._shutdown_event.is_set()


def async_exec(timeout: int | None = None):
    """
    装饰器：将同步函数转换为异步执行

    Args:
        timeout: 超时时间（秒）

    Example:
        @async_exec(timeout=30)
        def blocking_operation():
            # 耗时操作
            pass

        # 使用
        result = await blocking_operation()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            executor = ThreadPoolExecutor()
            return await executor.submit(func, *args, **kwargs, timeout=timeout)

        return wrapper

    return decorator


def get_executor() -> ThreadPoolExecutor:
    """获取全局线程池执行器实例"""
    return ThreadPoolExecutor()


# 全局执行器实例
_executor_instance = ThreadPoolExecutor()
