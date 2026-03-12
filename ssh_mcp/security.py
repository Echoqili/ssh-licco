"""
SSH LICCO Security Module
安全验证和防护模块
"""

import re
import shlex
from typing import Set, Optional
from pathlib import Path


class SecurityError(Exception):
    """安全异常类"""
    pass


class CommandValidator:
    """命令验证器 - 防止命令注入攻击"""
    
    # 默认允许的命令白名单
    DEFAULT_ALLOWED_COMMANDS: Set[str] = {
        # 基础命令
        'ls', 'dir', 'cd', 'pwd', 'cat', 'head', 'tail', 'less', 'more',
        'grep', 'find', 'which', 'whereis',
        
        # 系统信息
        'uname', 'hostname', 'whoami', 'uptime', 'date', 'cal',
        'top', 'htop', 'ps', 'free', 'df', 'du',
        
        # 网络
        'ping', 'netstat', 'ss', 'curl', 'wget', 'dig', 'nslookup',
        
        # 文件操作
        'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'touch', 'chmod', 'chown',
        'ln', 'tar', 'gzip', 'zip', 'unzip',
        
        # 文本处理
        'echo', 'printf', 'sed', 'awk', 'cut', 'sort', 'uniq', 'wc',
        
        # Docker
        'docker', 'docker-compose',
        
        # 系统管理
        'systemctl', 'journalctl', 'service',
    }
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'\|',          # 管道
        r'&',           # 后台执行
        r';',           # 命令分隔
        r'\$\(',        # 命令替换 $()
        r'`',           # 命令替换 ``
        r'>',           # 重定向
        r'<',           # 输入重定向
        r'\n',          # 换行注入
        r'\r',          # 回车注入
    ]
    
    def __init__(self, allowed_commands: Optional[Set[str]] = None, strict_mode: bool = True):
        """
        初始化命令验证器
        
        Args:
            allowed_commands: 允许的命令集合
            strict_mode: 严格模式（启用所有检查）
        """
        self.allowed_commands = allowed_commands or self.DEFAULT_ALLOWED_COMMANDS.copy()
        self.strict_mode = strict_mode
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译危险模式正则"""
        self.dangerous_regex = [
            re.compile(pattern) for pattern in self.DANGEROUS_PATTERNS
        ]
    
    def validate_command(self, command: str) -> bool:
        """
        验证命令是否安全
        
        Args:
            command: 要验证的命令
            
        Returns:
            bool: 是否安全
            
        Raises:
            SecurityError: 如果命令不安全
        """
        if not command or not command.strip():
            raise SecurityError("命令不能为空")
        
        # 分割命令获取基础命令
        try:
            cmd_parts = shlex.split(command)
        except ValueError as e:
            raise SecurityError(f"命令格式错误：{e}")
        
        if not cmd_parts:
            raise SecurityError("命令不能为空")
        
        base_command = cmd_parts[0]
        
        # 1. 检查白名单
        if base_command not in self.allowed_commands:
            raise SecurityError(
                f"命令 '{base_command}' 不在允许列表中。"
                f"允许的命令：{', '.join(sorted(list(self.allowed_commands)[:8]))}..."
            )
        
        # 2. 严格模式下检查危险字符
        if self.strict_mode:
            for regex in self.dangerous_regex:
                if regex.search(command):
                    raise SecurityError(
                        f"命令包含危险字符，可能被用于命令注入"
                    )
        
        # 3. 检查命令长度
        if len(command) > 4096:
            raise SecurityError("命令过长（最大 4096 字符）")
        
        # 4. 检查特殊关键字
        dangerous_keywords = ['sudo', 'passwd', 'shadow', '/etc/', '/root/']
        for keyword in dangerous_keywords:
            if keyword in command.lower():
                raise SecurityError(f"命令包含受限关键字：'{keyword}'")
        
        return True


class PathValidator:
    """路径验证器 - 防止路径遍历攻击"""
    
    # 禁止访问的路径
    FORBIDDEN_PATHS = [
        '/etc', '/root', '/boot', '/proc', '/sys',
        '/var/log', '/var/spool', '/var/cache',
    ]
    
    def __init__(self, base_dir: str = '/home', strict_mode: bool = True):
        """
        初始化路径验证器
        
        Args:
            base_dir: 基础目录
            strict_mode: 严格模式
        """
        self.base_dir = Path(base_dir).resolve()
        self.strict_mode = strict_mode
    
    def validate_path(self, user_path: str) -> Path:
        """
        验证用户提供的路径
        
        Args:
            user_path: 用户提供的路径
            
        Returns:
            Path: 验证后的安全路径
            
        Raises:
            SecurityError: 如果路径不安全
        """
        if not user_path or not user_path.strip():
            raise SecurityError("路径不能为空")
        
        # 转换为绝对路径
        full_path = (self.base_dir / user_path).resolve()
        
        # 1. 检查路径遍历（确保在 base_dir 内）
        if not str(full_path).startswith(str(self.base_dir)):
            raise SecurityError("路径遍历攻击被阻止！")
        
        # 2. 检查禁止路径
        path_str = str(full_path)
        for forbidden in self.FORBIDDEN_PATHS:
            if path_str.startswith(forbidden):
                raise SecurityError(f"禁止访问敏感路径：{forbidden}")
        
        return full_path


# 全局验证器实例
command_validator = CommandValidator(strict_mode=True)
path_validator = PathValidator(base_dir='/home', strict_mode=True)
