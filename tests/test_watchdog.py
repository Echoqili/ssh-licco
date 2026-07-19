from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ssh_mcp.watchdog import (
    GlobalExceptionHandler,
    Watchdog,
    WatchdogEvent,
    WatchdogStatus,
    get_watchdog,
    setup_global_exception_handler,
)


class TestWatchdogStatus:
    def test_values(self):
        assert WatchdogStatus.RUNNING.value == "running"
        assert WatchdogStatus.STOPPED.value == "stopped"
        assert WatchdogStatus.PAUSED.value == "paused"


class TestWatchdogEvent:
    def test_creation(self):
        event = WatchdogEvent(
            timestamp=datetime.now(),
            event_type="TEST",
            message="test event",
        )
        assert event.event_type == "TEST"
        assert event.message == "test event"
        assert event.details == {}

    def test_with_details(self):
        event = WatchdogEvent(
            timestamp=datetime.now(),
            event_type="TEST",
            message="test",
            details={"key": "value"},
        )
        assert event.details["key"] == "value"


class TestWatchdog:
    def setup_method(self):
        Watchdog._instance = None

    def _fresh_watchdog(self) -> Watchdog:
        Watchdog._instance = None
        return Watchdog()

    def test_singleton(self):
        w1 = Watchdog()
        w2 = Watchdog()
        assert w1 is w2

    def test_initial_status_stopped(self):
        w = self._fresh_watchdog()
        assert w.status == WatchdogStatus.STOPPED

    def test_register_task(self):
        w = self._fresh_watchdog()
        w.register_task("task-1", "Test Task", timeout=60)
        tasks = w.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == "task-1"

    def test_unregister_task(self):
        w = self._fresh_watchdog()
        w.register_task("task-1", "Test Task")
        w.unregister_task("task-1")
        assert len(w.get_tasks()) == 0

    def test_update_heartbeat(self):
        w = self._fresh_watchdog()
        w.register_task("task-1", "Test Task")
        old_hb = w.get_tasks()[0].last_heartbeat
        w.update_task_heartbeat("task-1")
        new_hb = w.get_tasks()[0].last_heartbeat
        assert new_hb >= old_hb

    def test_update_heartbeat_nonexistent(self):
        w = self._fresh_watchdog()
        w.update_task_heartbeat("nonexistent")

    def test_update_progress(self):
        w = self._fresh_watchdog()
        w.register_task("task-1", "Test Task")
        w.update_task_progress("task-1", 50)
        assert w.get_tasks()[0].progress == 50

    def test_capture_exception(self):
        w = self._fresh_watchdog()
        w.capture_exception(ValueError("test error"), context="test")
        events = w.get_events()
        assert len(events) >= 1
        assert events[0].event_type == "SYSTEM_ERROR"

    def test_get_events_limit(self):
        w = self._fresh_watchdog()
        for i in range(5):
            w.capture_exception(ValueError(f"error {i}"))
        events = w.get_events(limit=3)
        assert len(events) <= 3

    def test_add_recovery_callback(self):
        w = self._fresh_watchdog()
        callback = MagicMock()
        w.add_recovery_callback(callback)
        assert callback in w._recovery_callbacks

    def test_start_sets_running(self):
        w = self._fresh_watchdog()
        with patch.object(w, "_monitor_loop", MagicMock()):
            with patch("asyncio.create_task", return_value=MagicMock()):
                w.start()
        assert w.status == WatchdogStatus.RUNNING
        w.stop()

    def test_stop_sets_stopped(self):
        w = self._fresh_watchdog()
        with patch.object(w, "_monitor_loop", MagicMock()):
            with patch("asyncio.create_task", return_value=MagicMock()):
                w.start()
        w.stop()
        assert w.status == WatchdogStatus.STOPPED

    def test_start_already_running(self):
        w = self._fresh_watchdog()
        with patch.object(w, "_monitor_loop", MagicMock()):
            with patch("asyncio.create_task", return_value=MagicMock()):
                w.start()
        with patch.object(w, "_monitor_loop", MagicMock()):
            with patch("asyncio.create_task", return_value=MagicMock()):
                w.start()
        assert w.status == WatchdogStatus.RUNNING
        w.stop()


class TestGlobalExceptionHandler:
    def test_enable(self):
        handler = GlobalExceptionHandler()
        mock_loop = MagicMock()
        mock_loop.set_exception_handler = MagicMock()
        mock_loop.get_exception_handler = MagicMock(return_value=None)
        with patch("asyncio.get_event_loop", return_value=mock_loop):
            handler.enable()
        assert handler._enabled is True

    def test_disable(self):
        handler = GlobalExceptionHandler()
        mock_loop = MagicMock()
        mock_loop.set_exception_handler = MagicMock()
        mock_loop.get_exception_handler = MagicMock(return_value=None)
        mock_loop.set_exception_handler = MagicMock()
        with patch("asyncio.get_event_loop", return_value=mock_loop):
            handler.enable()
            handler.disable()
        assert handler._enabled is False

    def test_disable_not_enabled(self):
        handler = GlobalExceptionHandler()
        handler.disable()
        assert handler._enabled is False

    def test_enable_already_enabled(self):
        handler = GlobalExceptionHandler()
        handler._enabled = True
        handler.enable()
        assert handler._enabled is True


class TestGetWatchdog:
    def test_returns_watchdog(self):
        Watchdog._instance = None
        w = get_watchdog()
        assert isinstance(w, Watchdog)
