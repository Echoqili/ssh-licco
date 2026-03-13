"""
SSH LICCO Security Module
安全验证和防护模块 - 支持多级安全策略
"""

import re
import shlex
import os
from typing import Set, Optional
from pathlib import Path
from enum import Enum


class SecurityLevel(Enum):
    """安全级别枚举"""
    STRICT = "strict"        # 严格模式 - 生产环境
    BALANCED = "balanced"    # 平衡模式 - 默认
    RELAXED = "relaxed"      # 宽松模式 - 开发/测试


class SecurityError(Exception):
    """安全异常类"""
    pass


class CommandValidator:
    """命令验证器 - 防止命令注入攻击"""
    
    # 基础允许的命令白名单（所有模式都允许）
    BASE_ALLOWED_COMMANDS: Set[str] = {
        # 基础命令
        'ls', 'dir', 'cd', 'pwd', 'cat', 'head', 'tail', 'less', 'more',
        'grep', 'find', 'which', 'whereis',
        
        # 系统信息
        'uname', 'hostname', 'whoami', 'uptime', 'date', 'cal',
        'top', 'htop', 'ps', 'free', 'df', 'du',
        
        # 网络
        'ping', 'netstat', 'ss', 'dig', 'nslookup',
        
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
    
    # 扩展命令（仅在 relaxed 模式允许）
    EXTENDED_COMMANDS: Set[str] = {
        'sudo', 'su',
        'wget', 'curl',
        'apt-get', 'apt', 'yum', 'dnf', 'pacman',
        'pip', 'pip3', 'npm', 'yarn',
        'git', 'svn',
        'python3', 'python', 'node', 'java',
        'vim', 'vi', 'nano', 'emacs',
        'ssh', 'scp', 'rsync',
        'kill', 'pkill', 'killall',
    }
    
    # 危险字符模式（strict 模式检查）
    DANGEROUS_PATTERNS_STRICT = [
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
    
    # 危险字符模式（balanced 模式检查）
    DANGEROUS_PATTERNS_BALANCED = [
        r'\|',          # 管道
        r';',           # 命令分隔
        r'\$\(',        # 命令替换
        r'`',           # 命令替换
    ]
    
    # 危险关键字
    DANGEROUS_KEYWORDS = ['passwd', 'shadow', '/etc/shadow', '/root/.ssh']
    
    def __init__(
        self, 
        security_level: SecurityLevel = SecurityLevel.BALANCED,
        extra_allowed_commands: Optional[Set[str]] = None
    ):
        """
        初始化命令验证器
        
        Args:
            security_level: 安全级别
            extra_allowed_commands: 额外允许的命令
        """
        self.security_level = security_level
        self.extra_allowed_commands = extra_allowed_commands or set()
        self.allowed_commands = self._build_allowed_commands()
        self._compile_patterns()
        
        # 根据安全级别设置严格程度
        if security_level == SecurityLevel.STRICT:
            self.strict_mode = True
            self.dangerous_patterns = self.DANGEROUS_PATTERNS_STRICT
        elif security_level == SecurityLevel.BALANCED:
            self.strict_mode = True
            self.dangerous_patterns = self.DANGEROUS_PATTERNS_BALANCED
        else:  # RELAXED
            self.strict_mode = False
            self.dangerous_patterns = []
    
    def _build_allowed_commands(self) -> Set[str]:
        """构建允许的命令集合"""
        allowed = self.BASE_ALLOWED_COMMANDS.copy()
        
        # 在 relaxed 模式添加扩展命令
        if self.security_level == SecurityLevel.RELAXED:
            allowed.update(self.EXTENDED_COMMANDS)
        
        # 添加用户自定义命令
        allowed.update(self.extra_allowed_commands)
        
        return allowed
    
    def _compile_patterns(self):
        """编译危险模式正则"""
        self.dangerous_regex = [
            re.compile(pattern) for pattern in self.dangerous_patterns
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
            # 提供友好提示
            similar_cmds = self._find_similar_commands(base_command)
            hint = ""
            if similar_cmds:
                hint = f"\n提示：您可能是想用 {' 或 '.join(similar_cmds[:3])}？"
            
            raise SecurityError(
                f"命令 '{base_command}' 不在允许列表中。{hint}\n"
                f"当前安全级别：{self.security_level.value}\n"
                f"如需使用该命令，请设置环境变量：SSH_EXTRA_ALLOWED_COMMANDS={base_command}"
            )
        
        # 2. 严格模式下检查危险字符
        if self.strict_mode:
            for regex in self.dangerous_regex:
                if regex.search(command):
                    raise SecurityError(
                        f"命令包含危险字符，可能被用于命令注入。\n"
                        f"被阻止的命令：{command}"
                    )
        
        # 3. 检查命令长度
        if len(command) > 4096:
            raise SecurityError("命令过长（最大 4096 字符）")
        
        # 4. 检查特殊关键字
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in command.lower():
                raise SecurityError(
                    f"命令包含受限关键字：'{keyword}'\n"
                    f"这是为了保护系统安全，防止未授权访问敏感文件。"
                )
        
        return True
    
    def _find_similar_commands(self, cmd: str) -> list:
        """查找相似的允许命令（用于友好提示）"""
        similar = []
        for allowed in self.allowed_commands:
            # 简单的前缀匹配
            if allowed.startswith(cmd[:3]) and len(allowed) < len(cmd) + 3:
                similar.append(allowed)
                if len(similar) >= 5:
                    break
        return similar


class PathValidator:
    """路径验证器 - 防止路径遍历攻击"""
    
    # 禁止访问的路径
    FORBIDDEN_PATHS = [
        '/etc', '/root', '/boot', '/proc', '/sys',
        '/var/log', '/var/spool', '/var/cache',
    ]
    
    # relaxed 模式允许的路径
    RELAXED_ALLOWED_PATHS = [
        '/tmp', '/var/tmp',
        '/home', '/opt', '/srv',
        '/usr/local', '/usr/share',
    ]
    
    def __init__(
        self, 
        security_level: SecurityLevel = SecurityLevel.BALANCED,
        base_dir: str = '/home',
        extra_allowed_paths: Optional[list] = None
    ):
        """
        初始化路径验证器
        
        Args:
            security_level: 安全级别
            base_dir: 基础目录
            extra_allowed_paths: 额外允许的路径
        """
        self.security_level = security_level
        self.base_dir = Path(base_dir).resolve()
        self.extra_allowed_paths = extra_allowed_paths or []
        
        # 在 relaxed 模式扩展允许的路径
        if security_level == SecurityLevel.RELAXED:
            self.forbidden_paths = []  # 不限制
        else:
            self.forbidden_paths = self.FORBIDDEN_PATHS.copy()
    
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
        
        # 1. 检查路径遍历（strict 和 balanced 模式）
        if self.security_level in [SecurityLevel.STRICT, SecurityLevel.BALANCED]:
            if not str(full_path).startswith(str(self.base_dir)):
                raise SecurityError(
                    "路径遍历攻击被阻止！\n"
                    f"请求路径：{user_path}\n"
                    f"解析路径：{full_path}\n"
                    f"允许的基础路径：{self.base_dir}"
                )
        
        # 2. 检查禁止路径（strict 和 balanced 模式）
        if self.forbidden_paths:
            path_str = str(full_path)
            for forbidden in self.forbidden_paths:
                if path_str.startswith(forbidden):
                    raise SecurityError(
                        f"禁止访问敏感路径：{forbidden}\n"
                        f"这是为了保护系统关键文件。"
                    )
        
        return full_path


# 全局验证器实例（从环境变量读取配置）
def create_validators_from_env():
    """从环境变量创建验证器实例"""
    
    # 读取安全级别
    level_str = os.getenv('SSH_SECURITY_LEVEL', 'balanced').lower()
    try:
        security_level = SecurityLevel(level_str)
    except ValueError:
        security_level = SecurityLevel.BALANCED
        print(f"⚠️  未知的安全级别 '{level_str}'，使用默认值 'balanced'")
    
    # 读取额外允许的命令
    extra_commands_str = os.getenv('SSH_EXTRA_ALLOWED_COMMANDS', '')
    extra_commands = set()
    if extra_commands_str:
        extra_commands = set(cmd.strip() for cmd in extra_commands_str.split(',') if cmd.strip())
    
    # 读取基础目录
    base_dir = os.getenv('SSH_BASE_DIR', '/home')
    
    # 创建验证器
    command_validator = CommandValidator(
        security_level=security_level,
        extra_allowed_commands=extra_commands
    )
    
    path_validator = PathValidator(
        security_level=security_level,
        base_dir=base_dir
    )
    
    return command_validator, path_validator


# 创建全局实例
command_validator, path_validator = create_validators_from_env()
