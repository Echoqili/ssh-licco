from __future__ import annotations

import asyncio
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .logging_config import get_logger


class WatchdogStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"


@dataclass
class WatchdogEvent:
    timestamp: datetime
    event_type: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class TaskInfo:
    task_id: str
    name: str
    status: str
    started_at: datetime
    last_heartbeat: datetime
    timeout: int | None = None
    progress: int = 0


class Watchdog:
    """
    看门狗监控器 - 监控系统健康状态和任务执行
    
    特性：
    - 全局异常捕获和处理
    - 任务超时检测
    - 心跳监控
    - 自动恢复机制
    - 事件日志记录
    """

    _instance: Watchdog | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._logger = get_logger("Watchdog")
        self._status: WatchdogStatus = WatchdogStatus.STOPPED
        self._tasks: dict[str, TaskInfo] = {}
        self._events: list[WatchdogEvent] = []
        self._event_lock = threading.Lock()
        self._task_lock = threading.Lock()
        self._monitor_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._recovery_callbacks: list[Callable[[WatchdogEvent], None]] = []
        self._initialized = True

    @property
    def status(self) -> WatchdogStatus:
        return self._status

    def start(self) -> None:
        """启动看门狗监控"""
        if self._status == WatchdogStatus.RUNNING:
            self._logger.warning("Watchdog is already running")
            return

        self._status = WatchdogStatus.RUNNING
        self._shutdown_event.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._logger.info("Watchdog started")

    def stop(self) -> None:
        """停止看门狗监控"""
        self._status = WatchdogStatus.STOPPED
        self._shutdown_event.set()
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        self._logger.info("Watchdog stopped")

    async def _monitor_loop(self):
        """监控主循环"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(5)
                await self._check_timeouts()
                await self._cleanup_old_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Watchdog monitor loop error: {e}")

    async def _check_timeouts(self):
        """检查任务超时"""
        now = datetime.now()
        timeout_tasks = []

        with self._task_lock:
            for task_id, task_info in self._tasks.items():
                if task_info.timeout:
                    elapsed = (now - task_info.last_heartbeat).total_seconds()
                    if elapsed > task_info.timeout:
                        timeout_tasks.append(task_id)

        for task_id in timeout_tasks:
            await self._handle_timeout(task_id)

    async def _handle_timeout(self, task_id: str):
        """处理任务超时"""
        with self._task_lock:
            task_info = self._tasks.get(task_id)

        if task_info:
            event = WatchdogEvent(
                timestamp=datetime.now(),
                event_type="TASK_TIMEOUT",
                message=f"Task '{task_info.name}' timed out",
                details={
                    "task_id": task_id,
                    "task_name": task_info.name,
                    "timeout": task_info.timeout,
                    "started_at": task_info.started_at.isoformat(),
                    "last_heartbeat": task_info.last_heartbeat.isoformat()
                }
            )
            self._log_event(event)
            await self._trigger_recovery(event)

            with self._task_lock:
                self._tasks.pop(task_id, None)

    async def _cleanup_old_events(self):
        """清理旧事件（保留最近100条）"""
        with self._event_lock:
            if len(self._events) > 100:
                self._events = self._events[-100:]

    def register_task(self, task_id: str, name: str, timeout: int | None = None) -> None:
        """注册监控任务"""
        with self._task_lock:
            self._tasks[task_id] = TaskInfo(
                task_id=task_id,
                name=name,
                status="running",
                started_at=datetime.now(),
                last_heartbeat=datetime.now(),
                timeout=timeout,
                progress=0
            )
        self._logger.debug(f"Registered task: {task_id} ({name})")

    def update_task_heartbeat(self, task_id: str) -> None:
        """更新任务心跳"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.last_heartbeat = datetime.now()

    def update_task_progress(self, task_id: str, progress: int) -> None:
        """更新任务进度"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress
                task.last_heartbeat = datetime.now()

    def unregister_task(self, task_id: str) -> None:
        """注销任务"""
        with self._task_lock:
            self._tasks.pop(task_id, None)
        self._logger.debug(f"Unregistered task: {task_id}")

    def _log_event(self, event: WatchdogEvent) -> None:
        """记录事件"""
        with self._event_lock:
            self._events.append(event)

        log_level = {
            "TASK_TIMEOUT": "ERROR",
            "SYSTEM_ERROR": "ERROR",
            "CONNECTION_LOST": "ERROR",
            "RECOVERY_SUCCESS": "INFO",
            "RECOVERY_FAILED": "ERROR",
            "WARNING": "WARNING"
        }.get(event.event_type, "INFO")

        log_method = getattr(self._logger, log_level.lower(), self._logger.info)
        log_method(f"[{event.event_type}] {event.message}")

    async def _trigger_recovery(self, event: WatchdogEvent) -> None:
        """触发恢复回调"""
        for callback in self._recovery_callbacks:
            try:
                callback(event)
            except Exception as e:
                self._logger.error(f"Recovery callback failed: {e}")

    def add_recovery_callback(self, callback: Callable[[WatchdogEvent], None]) -> None:
        """添加恢复回调"""
        self._recovery_callbacks.append(callback)

    def get_events(self, limit: int = 20) -> list[WatchdogEvent]:
        """获取最近事件"""
        with self._event_lock:
            return list(reversed(self._events[-limit:]))

    def get_tasks(self) -> list[TaskInfo]:
        """获取所有监控任务"""
        with self._task_lock:
            return list(self._tasks.values())

    def capture_exception(self, exc: Exception, context: str = "") -> None:
        """捕获并记录异常"""
        event = WatchdogEvent(
            timestamp=datetime.now(),
            event_type="SYSTEM_ERROR",
            message=f"Exception captured: {str(exc)}",
            details={
                "exception_type": type(exc).__name__,
                "context": context,
                "traceback": traceback.format_exc()
            }
        )
        self._log_event(event)


class GlobalExceptionHandler:
    """
    全局异常处理器
    
    特性：
    - 捕获未处理异常
    - 记录异常信息
    - 提供优雅的错误恢复
    """

    def __init__(self):
        self._logger = get_logger("GlobalExceptionHandler")
        self._watchdog = Watchdog()
        self._original_excepthook = None
        self._enabled = False

    def enable(self) -> None:
        """启用全局异常处理"""
        if self._enabled:
            return

        self._original_excepthook = asyncio.get_event_loop().get_exception_handler()
        asyncio.get_event_loop().set_exception_handler(self._handle_async_exception)

        import sys
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_sync_exception

        self._enabled = True
        self._logger.info("Global exception handler enabled")

    def disable(self) -> None:
        """禁用全局异常处理"""
        if not self._enabled:
            return

        asyncio.get_event_loop().set_exception_handler(self._original_excepthook)

        import sys
        sys.excepthook = self._original_excepthook

        self._enabled = False
        self._logger.info("Global exception handler disabled")

    def _handle_async_exception(self, loop: asyncio.AbstractEventLoop, context: dict) -> None:
        """处理异步异常"""
        exc = context.get('exception')
        if exc:
            self._watchdog.capture_exception(exc, context.get('message', ''))

        if self._original_excepthook:
            self._original_excepthook(loop, context)
        else:
            loop.default_exception_handler(context)

    def _handle_sync_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """处理同步异常"""
        if exc_value:
            self._watchdog.capture_exception(exc_value)

        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_traceback)
        else:
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)


def get_watchdog() -> Watchdog:
    """获取看门狗实例"""
    return Watchdog()


def setup_global_exception_handler() -> GlobalExceptionHandler:
    """设置全局异常处理器"""
    handler = GlobalExceptionHandler()
    handler.enable()
    return handler
