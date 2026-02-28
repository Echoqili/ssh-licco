from __future__ import annotations

import asyncio
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from .connection_config import ConnectionConfig


class SessionState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    EXECUTING = "executing"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class SessionInfo:
    session_id: str
    host: str
    port: int
    username: str
    state: SessionState
    connected_at: datetime
    last_activity: datetime
    command_count: int = 0
    error_message: Optional[str] = None


class SSHSession:
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.client: Optional[SSHClient] = None
        self.session_id = str(uuid.uuid4())
        self._state = SessionState.DISCONNECTED
        self._connected_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == SessionState.CONNECTED and self.client is not None

    async def connect(self) -> SessionInfo:
        async with self._lock:
            if self.is_connected:
                return self._get_session_info()
            
            self._state = SessionState.CONNECTING
            
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._connect_sync
                )
                self._connected_at = datetime.now()
                self._state = SessionState.CONNECTED
                return self._get_session_info()
            except Exception as e:
                self._state = SessionState.ERROR
                raise ConnectionError(f"Failed to connect to {self.config.host}: {str(e)}")

    def _connect_sync(self) -> None:
        self.client = SSHClient()
        self.client.set_missing_host_key_policy(AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': self.config.host,
            'port': self.config.port,
            'username': self.config.username,
            'timeout': self.config.timeout,
            'compress': self.config.compress,
            'look_for_keys': self.config.look_for_keys,
            'allow_agent': self.config.allow_agent,
        }
        
        if self.config.auth_method == "password" and self.config.password:
            connect_kwargs['password'] = self.config.password
        elif self.config.auth_method == "private_key" and self.config.private_key_path:
            connect_kwargs['key_filename'] = str(self.config.private_key_path)
            if self.config.passphrase:
                connect_kwargs['passphrase'] = self.config.passphrase
        
        self.client.connect(**connect_kwargs)

    async def execute_command(self, command: str, timeout: int = 30) -> dict:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        async with self._lock:
            self._state = SessionState.EXECUTING
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._execute_command_sync, command, timeout
                )
                return result
            finally:
                self._state = SessionState.CONNECTED

    def _execute_command_sync(self, command: str, timeout: int) -> dict:
        assert self.client is not None
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode('utf-8', errors='replace')
        stderr_data = stderr.read().decode('utf-8', errors='replace')
        
        return {
            "exit_code": exit_code,
            "stdout": stdout_data,
            "stderr": stderr_data,
            "session_id": self.session_id
        }

    async def execute_command_stream(
        self, command: str
    ) -> AsyncIterator[str]:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        async with self._lock:
            self._state = SessionState.EXECUTING
            try:
                async for line in asyncio.get_event_loop().run_in_executor(
                    None, self._execute_command_stream_sync, command
                ):
                    yield line
            finally:
                self._state = SessionState.CONNECTED

    def _execute_command_stream_sync(self, command: str) -> AsyncIterator[str]:
        assert self.client is not None
        
        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            yield line.decode('utf-8', errors='replace')

    async def open_shell(self, term: str = "xterm", width: int = 80, height: int = 24) -> paramiko.Channel:
        if not self.is_connected:
            raise ConnectionError("Not connected to SSH server")
        
        return await asyncio.get_event_loop().run_in_executor(
            None, self._open_shell_sync, term, width, height
        )

    def _open_shell_sync(self, term: str, width: int, height: int) -> paramiko.Channel:
        assert self.client is not None
        return self.client.invoke_shell(term=term, width=width, height=height)

    async def disconnect(self) -> None:
        async with self._lock:
            if self.client:
                self.client.close()
                self.client = None
            self._state = SessionState.DISCONNECTED

    def _get_session_info(self) -> SessionInfo:
        return SessionInfo(
            session_id=self.session_id,
            host=self.config.host,
            port=self.config.port,
            username=self.config.username,
            state=self._state,
            connected_at=self._connected_at or datetime.now(),
            last_activity=datetime.now()
        )


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, SSHSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, config: ConnectionConfig) -> SessionInfo:
        async with self._lock:
            session = SSHSession(config)
            session_info = await session.connect()
            self._sessions[session.session_id] = session
            return session_info

    async def get_session(self, session_id: str) -> Optional[SSHSession]:
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await session.disconnect()

    async def close_all_sessions(self) -> None:
        async with self._lock:
            for session in list(self._sessions.values()):
                await session.disconnect()
            self._sessions.clear()

    def list_sessions(self) -> list[SessionInfo]:
        return [
            session._get_session_info()
            for session in self._sessions.values()
        ]
