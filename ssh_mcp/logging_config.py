from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class SSHLogger:
    """SSH 日志管理器"""
    
    _instance: Optional[logging.Logger] = None
    _initialized: bool = False
    
    @classmethod
    def get_logger(cls, name: str = "ssh-licco") -> logging.Logger:
        """获取日志实例（单例模式）"""
        if cls._instance is None:
            cls._instance = logging.getLogger(name)
            if not cls._initialized:
                cls._setup_logger(cls._instance)
                cls._initialized = True
        return cls._instance
    
    @classmethod
    def _setup_logger(cls, logger: logging.Logger) -> None:
        """配置日志器"""
        if logger.handlers:
            return
        
        logger.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    @classmethod
    def set_log_level(cls, level: str) -> None:
        """设置日志级别"""
        if cls._instance:
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
            }
            cls._instance.setLevel(level_map.get(level.upper(), logging.INFO))
    
    @classmethod
    def add_file_handler(cls, log_path: str | Path, level: str = 'DEBUG') -> None:
        """添加文件日志处理器"""
        if cls._instance is None:
            cls.get_logger()
        
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        cls._instance.addHandler(file_handler)


def get_logger(name: str = "ssh-licco") -> logging.Logger:
    """便捷函数：获取日志实例"""
    return SSHLogger.get_logger(name)
