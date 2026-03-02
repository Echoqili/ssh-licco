from __future__ import annotations

import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AuditEventType(Enum):
    """审计事件类型"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    COMMAND_EXECUTE = "command_execute"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    ERROR = "error"


class AuditLogger:
    """
    审计日志管理器
    
    特性：
    - 结构化审计日志
    - 用户操作记录
    - 满足合规审计要求
    """
    
    _instance: Optional['AuditLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __init__(
        self,
        audit_log_path: Optional[str | Path] = None,
        log_level: int = logging.INFO
    ):
        self._audit_log_path = audit_log_path
        self._log_level = log_level
        self._extra_fields: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(
        cls,
        audit_log_path: Optional[str | Path] = None,
        log_level: int = logging.INFO
    ) -> 'AuditLogger':
        """获取审计日志单例"""
        if cls._instance is None:
            cls._instance = cls(audit_log_path, log_level)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """初始化审计日志器"""
        if self._audit_log_path:
            self._audit_log_path = Path(self._audit_log_path)
            self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._logger = logging.getLogger("ssh-audit")
        self._logger.setLevel(self._log_level)
        
        if not self._logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self._log_level)
            
            formatter = logging.Formatter(
                '%(asctime)s | AUDIT | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
            
            if self._audit_log_path:
                file_handler = logging.FileHandler(
                    self._audit_log_path,
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
    
    def set_extra_fields(self, **kwargs) -> None:
        """设置额外字段"""
        self._extra_fields.update(kwargs)
    
    def log(
        self,
        event_type: AuditEventType,
        username: str,
        host: str,
        action: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> None:
        """记录审计日志"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "username": username,
            "host": host,
            "action": action,
            "result": result,
            "session_id": session_id,
            "details": details or {},
            **self._extra_fields
        }
        
        log_message = json.dumps(audit_entry, ensure_ascii=False, default=str)
        self._logger.info(log_message)
    
    def log_connect(
        self,
        username: str,
        host: str,
        port: int,
        client_type: str,
        session_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """记录连接事件"""
        self.log(
            event_type=AuditEventType.CONNECT,
            username=username,
            host=host,
            action=f"SSH connect to {host}:{port}",
            result="success" if success else "failed",
            details={
                "port": port,
                "client_type": client_type,
                "error_message": error_message
            },
            session_id=session_id
        )
    
    def log_disconnect(
        self,
        username: str,
        host: str,
        session_id: str,
        duration_seconds: Optional[float] = None
    ) -> None:
        """记录断开连接事件"""
        self.log(
            event_type=AuditEventType.DISCONNECT,
            username=username,
            host=host,
            action=f"SSH disconnect from {host}",
            result="success",
            details={
                "session_id": session_id,
                "duration_seconds": duration_seconds
            },
            session_id=session_id
        )
    
    def log_command(
        self,
        username: str,
        host: str,
        command: str,
        return_code: int,
        stdout_length: int,
        stderr_length: int,
        session_id: Optional[str] = None,
        execution_time_ms: Optional[float] = None
    ) -> None:
        """记录命令执行事件"""
        self.log(
            event_type=AuditEventType.COMMAND_EXECUTE,
            username=username,
            host=host,
            action=f"Execute command: {command[:100]}",
            result="success" if return_code == 0 else "failed",
            details={
                "command": command,
                "return_code": return_code,
                "stdout_length": stdout_length,
                "stderr_length": stderr_length,
                "execution_time_ms": execution_time_ms
            },
            session_id=session_id
        )
    
    def log_file_transfer(
        self,
        event_type: AuditEventType,
        username: str,
        host: str,
        file_path: str,
        file_size: int,
        direction: str,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """记录文件传输事件"""
        self.log(
            event_type=event_type,
            username=username,
            host=host,
            action=f"{direction} file: {file_path}",
            result="success" if success else "failed",
            details={
                "file_path": file_path,
                "file_size": file_size,
                "direction": direction,
                "error_message": error_message
            },
            session_id=session_id
        )
    
    def log_auth(
        self,
        username: str,
        host: str,
        auth_method: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """记录认证事件"""
        self.log(
            event_type=AuditEventType.AUTH_SUCCESS if success else AuditEventType.AUTH_FAILED,
            username=username,
            host=host,
            action=f"SSH authentication using {auth_method}",
            result="success" if success else "failed",
            details={
                "auth_method": auth_method,
                "error_message": error_message
            }
        )


def get_audit_logger(
    audit_log_path: Optional[str | Path] = None,
    log_level: int = logging.INFO
) -> AuditLogger:
    """便捷函数：获取审计日志实例"""
    return AuditLogger.get_instance(audit_log_path, log_level)
