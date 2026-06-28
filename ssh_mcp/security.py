"""
SSH-LICCO Security Module
安全验证和防护模块 - 支持多级安全策略
"""

import os
import re
import shlex
from enum import Enum
from pathlib import Path, PurePosixPath


class SecurityLevel(Enum):
    """安全级别枚举"""
    STRICT = "strict"        # 严格模式 - 生产环境
    BALANCED = "balanced"    # 平衡模式 - 默认
    RELAXED = "relaxed"      # 宽松模式 - 开发/测试


class RiskLevel(Enum):
    """风险级别枚举"""
    SAFE = "safe"           # 安全 - 无风险
    LOW = "low"             # 低风险 - 轻微影响
    MEDIUM = "medium"       # 中风险 - 需要注意
    HIGH = "high"           # 高风险 - 需要确认
    CRITICAL = "critical"   # 严重风险 - 需要多次确认


class SecurityError(Exception):
    """安全异常类"""
    pass


class CommandValidator:
    """命令验证器 - 防止命令注入攻击"""

    # 基础允许的命令白名单（所有模式都允许）
    BASE_ALLOWED_COMMANDS: set[str] = {
        # Shell
        'bash', 'sh', 'zsh', 'csh', 'tcsh', 'ksh', 'dash',

        # 基础命令
        'ls', 'dir', 'cd', 'pwd', 'cat', 'head', 'tail', 'less', 'more',
        'grep', 'egrep', 'fgrep', 'find', 'which', 'whereis', 'type',

        # 系统信息
        'uname', 'hostname', 'whoami', 'id', 'uptime', 'date', 'cal',
        'top', 'htop', 'ps', 'free', 'df', 'du', 'vmstat', 'iostat', 'mpstat',

        # 网络
        'ping', 'ping6', 'netstat', 'ss', 'dig', 'nslookup', 'host',
        'nc', 'telnet', 'traceroute', 'mtr',

        # 文件操作
        'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'touch', 'chmod', 'chown', 'chgrp',
        'ln', 'tar', 'gzip', 'gunzip', 'bzip2', 'bzcat', 'zip', 'unzip',
        'rsync', 'scp', 'sftp', 'rsync',

        # 文本处理
        'echo', 'printf', 'sed', 'awk', 'cut', 'sort', 'uniq', 'wc',
        'tr', 'nl', 'fmt', 'fold', 'paste', 'join',

        # Docker & Container
        'docker', 'docker-compose', 'docker-compose-v2', 'podman', 'containerd', 'runc',

        # 系统管理
        'systemctl', 'journalctl', 'service', 'init', 'reboot', 'shutdown', 'poweroff',

        # 开发工具
        'git', 'git-lfs', 'svn', 'hg', 'make', 'cmake', 'autoconf', 'automake',
        'gcc', 'g++', 'clang', 'rustc', 'cargo', 'go', 'npm', 'yarn', 'npx',
        'python', 'python3', 'pip', 'pip3', 'node', 'nodejs', 'java', 'javac',
        'mvn', 'gradle', 'dotnet', 'csharp', 'ruby', 'rails', 'bundle',

        # 包管理
        'apt-get', 'apt', 'apt-cache', 'apt-key', 'dpkg', 'dpkg-deb',
        'yum', 'dnf', 'rpm', 'dnf-yum',
        'pacman', 'makepkg',
        'brew', 'port',

        # 文本编辑器
        'vim', 'vi', 'nano', 'emacs', 'nedit', 'pico', 'joe',

        # 进程管理
        'kill', 'pkill', 'killall', 'nice', 'renice', 'bg', 'fg', 'jobs',

        # 后台/会话/等待（部署、压测、构建等长任务必需）
        'sleep', 'nohup', 'setsid', 'disown', 'wait',
        'screen', 'tmux', 'byobu',
        'timeout', 'watch', 'time',
        'true', 'false', 'test', '[', 'eval',

        # 安全工具
        'chpasswd', 'passwd', 'openssl', 'gpg', 'ssh-keygen', 'ssh-agent',

        # 实用工具
        'wget', 'curl', 'httpie', 'jq', 'curlftpfs', 'ncftp',

        # 数据库
        'mysql', 'mysqladmin', 'mysqldump', 'psql', 'pg_dump', 'pg_restore',
        'mongosh', 'mongodump', 'mongorestore', 'redis-cli', 'redis-server',

        # 监控工具
        'prometheus', 'grafana-server', 'telegraf', 'influxd', 'zabbix', 'nagios',

        # Web 服务器（运维常用，之前遗漏导致 relaxed 之外的模式被拦截）
        'nginx', 'nginx-debug', 'apache2', 'apache2ctl', 'httpd',
        'caddy', 'haproxy', 'traefik', 'envoy', 'openresty', 'tengine',

        # Node.js 进程管理
        'pm2', 'forever', 'nodemon',

        # 系统硬件信息
        'lscpu', 'lsblk', 'lspci', 'lsusb',

        # 网络配置
        'ip', 'ifconfig', 'route', 'arp',

        # 包管理（补充）
        'snap',

        # 文本处理（补充）
        'xargs',
    }

    # 扩展命令（仅在 relaxed 模式允许）
    EXTENDED_COMMANDS: set[str] = {
        'sudo', 'su', 'doas',
        'rm', 'rmdir',
        'shutdown', 'reboot', 'poweroff', 'halt',
        'chmod', 'chown', 'chgrp',
        'mount', 'umount', 'fsck', 'mkfs',
        'dd', 'fdisk', 'parted', 'lvcreate', 'vgcreate',
        'useradd', 'userdel', 'groupadd', 'groupdel',
        'setfacl', 'getfacl', 'chcon', 'restorecon',
        'iptables', 'ip6tables', 'firewalld', 'ufw',
        'systemctl', 'service',
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

    # relaxed 模式黑名单：即使宽松模式也必须阻止的高危命令模式
    # relaxed 不再使用白名单，改为黑名单机制——只阻止已知高危操作
    RELAXED_BLOCKED_PATTERNS = [
        r'rm\s+-rf\s+/(?:\s|$)',          # rm -rf /  (根目录递归删除)
        r'rm\s+-rf\s+/\*',                # rm -rf /*
        r'rm\s+-fr\s+/(?:\s|$)',          # rm -fr /
        r'rm\s+-rf\s+/[^\s]+/\*',         # rm -rf /任意路径/*  (递归删除任意子目录内容)
        r'rm\s+-rf\s+/[^\s]+',             # rm -rf /任意路径    (递归删除任意绝对路径)
        r'mkfs\.\w+',                      # mkfs.*  (格式化文件系统)
        r'dd\s+if=/dev/(?:zero|random|urandom)\s+of=/dev/sd',  # dd 覆写磁盘
        r'dd\s+if=/dev/(?:zero|random|urandom)\s+of=/dev/nvm', # dd 覆写 NVMe
        r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;',  # fork bomb :(){ :|:& };:
        r'chmod\s+-R\s+777\s+/(?:\s|$)',  # chmod -R 777 /
        r'chmod\s+-R\s+000\s+/(?:\s|$)',  # chmod -R 000 /
        r'>\s*/dev/sd[a-z]',              # 写裸磁盘设备
        r'>\s*/dev/nvme',                 # 写裸 NVMe 设备
        r'shutdown\s+now',                # 立即关机
        r'poweroff\s+-f',                 # 强制关机
        r'reboot\s+-f',                   # 强制重启
        r'init\s+0',                      # 关机
        r'killall\s+-9\s+',               # killall -9 (批量强杀)
        r'pkill\s+-9\s+',                 # pkill -9 (批量强杀)
    ]

    # 危险关键字
    DANGEROUS_KEYWORDS = ['passwd', 'shadow', '/etc/shadow', '/root/.ssh']

    # 多层安全确认配置
    MULTI_LAYER_CONFIRMATION_ENABLED = True  # 是否启用多层确认
    CONFIRMATION_LAYERS = {
        RiskLevel.CRITICAL: 3,  # 严重风险需要3次确认
        RiskLevel.HIGH: 2,      # 高风险需要2次确认
        RiskLevel.MEDIUM: 1,    # 中风险需要1次确认
        RiskLevel.LOW: 0,       # 低风险不需要确认
        RiskLevel.SAFE: 0,      # 安全不需要确认
    }

    # 危险命令分类和风险评估
    DANGEROUS_COMMAND_PATTERNS = {
        # 删除操作 - 最高风险
        RiskLevel.CRITICAL: [
            r'rm\s+-rf\s+/',          # rm -rf / (根目录删除)
            r'rm\s+-rf\s+/\*',        # rm -rf /*
            r'rm\s+-fr\s+/',          # rm -fr /
            r'rm\s+-rf\s+/[^/]+/\*',  # rm -rf /path/*
            r'rm\s+-rf\s+/[^/]+$',    # rm -rf /path
            r'shred\s+-.*\s+/',       # shred 安全删除
        ],
        # 系统操作 - 高风险
        RiskLevel.HIGH: [
            r'reboot',                # 重启系统
            r'shutdown',              # 关机系统
            r'poweroff',              # 强制关机
            r'init\s+0',              # 关机
            r'rm\s+-rf\s+',           # 任何 rm -rf 操作
            r'rm\s+-fr\s+',           # 任何 rm -fr 操作
        ],
        # 文件系统操作 - 中高风险
        RiskLevel.MEDIUM: [
            r'mkfs\.\w+',             # 格式化文件系统
            r'fdisk',                 # 磁盘分区
            r'parted',                # 磁盘分区工具
            r'dd\s+if=/dev/',         # dd 操作磁盘设备
            r'mount\s+.*\s+/',        # 挂载到根目录
            r'chmod\s+-R\s+777\s+/',  # 递归设置根目录权限
            r'userdel',               # 删除用户
            r'groupdel',              # 删除组
        ],
        # 网络和防火墙操作 - 中等风险
        RiskLevel.LOW: [
            r'iptables',              # 防火墙规则
            r'firewalld',             # 防火墙管理
            r'ufw',                   # Ubuntu防火墙
            r'route\s+del',           # 删除路由
        ],
    }

    # 风险描述和警告消息
    RISK_DESCRIPTIONS = {
        RiskLevel.CRITICAL: "🔴 严重风险 - 可能导致系统完全损坏或数据永久丢失",
        RiskLevel.HIGH: "🟠 高风险 - 可能影响系统运行或导致重要数据丢失",
        RiskLevel.MEDIUM: "🟡 中等风险 - 可能影响系统配置或部分功能",
        RiskLevel.LOW: "🟢 低风险 - 轻微影响，但仍需注意",
        RiskLevel.SAFE: "✅ 安全 - 无明显风险",
    }

    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.BALANCED,
        extra_allowed_commands: set[str] | None = None
    ):
        """
        初始化命令验证器

        Args:
            security_level: 安全级别
            extra_allowed_commands: 额外允许的命令
        """
        self.security_level = security_level
        self.extra_allowed_commands = extra_allowed_commands or set()

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

        self.allowed_commands = self._build_allowed_commands()
        self._compile_patterns()
        
        # 编译风险评估正则表达式
        self._risk_pattern_regex = {}
        for risk_level, patterns in self.DANGEROUS_COMMAND_PATTERNS.items():
            self._risk_pattern_regex[risk_level] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        # relaxed 模式黑名单正则（独立编译，与白名单模式的 dangerous_regex 区分）
        self._relaxed_blocked_regex = [
            re.compile(pattern) for pattern in self.RELAXED_BLOCKED_PATTERNS
        ]

    @classmethod
    def from_config_file(
        cls,
        config_path: str,
        security_level: SecurityLevel = SecurityLevel.BALANCED,
    ) -> "CommandValidator":
        """从 JSON 配置文件加载命令白名单

        配置文件格式见 config/allowed_commands.example.json
        支持 base / extended / extra 三个分区，命令合并到内置白名单之上。

        Args:
            config_path: JSON 配置文件路径
            security_level: 安全级别
        """
        import json
        from pathlib import Path

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"命令白名单配置文件不存在: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 收集所有 extra 命令（用户自定义，叠加在 base 之上）
        extra_commands: set[str] = set()
        for section in ("base", "extended", "extra"):
            section_data = config.get(section, {})
            if isinstance(section_data, dict):
                # 按分类组织的命令
                for category_cmds in section_data.values():
                    if isinstance(category_cmds, list):
                        extra_commands.update(cmd for cmd in category_cmds if isinstance(cmd, str) and not cmd.startswith("_"))
            elif isinstance(section_data, list):
                extra_commands.update(cmd for cmd in section_data if isinstance(cmd, str))

        return cls(
            security_level=security_level,
            extra_allowed_commands=extra_commands,
        )

    def _build_allowed_commands(self) -> set[str]:
        """构建允许的命令集合"""
        allowed = self.BASE_ALLOWED_COMMANDS.copy()

        # 在 relaxed 模式添加扩展命令（兼容性保留，relaxed 实际用黑名单）
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

        # 1. relaxed 模式：黑名单机制（不检查白名单，只阻止高危命令）
        if self.security_level == SecurityLevel.RELAXED:
            for regex in self._relaxed_blocked_regex:
                if regex.search(command):
                    raise SecurityError(
                        f"命令匹配高危模式黑名单，已被阻止。\n"
                        f"被阻止的命令：{command}\n"
                        f"当前安全级别：relaxed（黑名单模式）\n"
                        f"如确需执行，请手动登录服务器操作。"
                    )
            # relaxed 模式跳过白名单和危险字符检查，直接通过
            # 仍检查命令长度
            if len(command) > 4096:
                raise SecurityError("命令过长（最大 4096 字符）")
            return True

        # 2. strict / balanced 模式：白名单机制
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

        # 3. 严格模式下检查危险字符
        if self.strict_mode:
            for regex in self.dangerous_regex:
                if regex.search(command):
                    raise SecurityError(
                        f"命令包含危险字符，可能被用于命令注入。\n"
                        f"被阻止的命令：{command}"
                    )

        # 4. 检查命令长度
        if len(command) > 4096:
            raise SecurityError("命令过长（最大 4096 字符）")

        # 5. 检查特殊关键字
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

    def assess_risk_level(self, command: str) -> RiskLevel:
        """
        评估命令的风险级别
        
        Args:
            command: 要评估的命令
            
        Returns:
            RiskLevel: 风险级别
        """
        # 按风险级别从高到低检查
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if risk_level in self._risk_pattern_regex:
                for regex in self._risk_pattern_regex[risk_level]:
                    if regex.search(command):
                        return risk_level
        
        return RiskLevel.SAFE

    def get_required_confirmations(self, command: str) -> int:
        """
        获取命令需要的确认次数
        
        Args:
            command: 要检查的命令
            
        Returns:
            int: 需要的确认次数
        """
        if not self.MULTI_LAYER_CONFIRMATION_ENABLED:
            return 0
        
        risk_level = self.assess_risk_level(command)
        return self.CONFIRMATION_LAYERS.get(risk_level, 0)

    def get_risk_description(self, command: str) -> tuple[RiskLevel, str]:
        """
        获取命令的风险描述
        
        Args:
            command: 要检查的命令
            
        Returns:
            tuple[RiskLevel, str]: 风险级别和描述信息
        """
        risk_level = self.assess_risk_level(command)
        description = self.RISK_DESCRIPTIONS.get(risk_level, "未知风险")
        return risk_level, description

    def generate_warning_message(self, command: str, layer: int = 1) -> str:
        """
        生成多层确认的警告消息
        
        Args:
            command: 要执行的命令
            layer: 当前确认层级（从1开始）
            
        Returns:
            str: 警告消息
        """
        risk_level, risk_description = self.get_risk_description(command)
        required_confirmations = self.get_required_confirmations(command)
        
        warning_header = {
            RiskLevel.CRITICAL: "🚨 严重危险操作警告",
            RiskLevel.HIGH: "⚠️  高风险操作警告", 
            RiskLevel.MEDIUM: "⚡ 中等风险操作提醒",
            RiskLevel.LOW: "📌 低风险操作提示",
            RiskLevel.SAFE: "✅ 安全操作确认",
        }
        
        message = f"""
{'=' * 60}
{warning_header.get(risk_level, '操作确认')}
{'=' * 60}

{risk_description}

📋 将要执行的命令：
   {command}

🔐 安全确认流程：
   当前层级：{layer}/{required_confirmations}
   剩余确认：{required_confirmations - layer}

{'⚠️  重要提醒：' if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH] else '💡 提示：'}
   {'此操作不可逆！请确保您完全理解其后果。' if risk_level == RiskLevel.CRITICAL else 
    '此操作可能影响系统稳定性，请谨慎操作。' if risk_level == RiskLevel.HIGH else
    '此操作可能影响系统配置，建议先备份。' if risk_level == RiskLevel.MEDIUM else
    '此操作影响较小，但建议仔细检查参数。'}

🛑 如需终止操作，请不设置 confirm_dangerous 参数
✅ 如确认执行，请设置 confirm_dangerous=true 并重试

{'=' * 60}
"""
        return message

    def check_multi_layer_confirmation(self, command: str, confirm_dangerous: bool = False, current_layer: int = 1) -> tuple[bool, str]:
        """
        检查多层安全确认
        
        Args:
            command: 要执行的命令
            confirm_dangerous: 是否已确认危险操作
            current_layer: 当前确认层级
            
        Returns:
            tuple[bool, str]: (是否允许执行, 消息)
        """
        if not self.MULTI_LAYER_CONFIRMATION_ENABLED:
            return True, ""
        
        required_confirmations = self.get_required_confirmations(command)
        
        if required_confirmations == 0:
            return True, ""
        
        # 如果没有确认，返回警告消息
        if not confirm_dangerous:
            warning_message = self.generate_warning_message(command, current_layer)
            return False, warning_message
        
        # 检查确认层级是否足够
        if current_layer < required_confirmations:
            next_warning = self.generate_warning_message(command, current_layer + 1)
            return False, f"需要更多确认层级才能执行此操作。\n\n{next_warning}"
        
        # 所有确认层级都已完成
        risk_level, risk_description = self.get_risk_description(command)
        return True, f"✅ 已完成 {required_confirmations} 层安全确认，允许执行 {risk_level.value} 风险操作。"


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
        extra_allowed_paths: list | None = None
    ):
        """
        初始化路径验证器
        
        Args:
            security_level: 安全级别
            base_dir: 基础目录（远程 Unix 路径）
            extra_allowed_paths: 额外允许的路径
        """
        self.security_level = security_level
        # 使用 PurePosixPath 而非 Path，因为路径始终是远程 Unix 服务器的路径
        # Path 在 Windows 上会变成 WindowsPath，导致路径比较失败
        self.base_dir = self._normalize_posix_path(PurePosixPath(base_dir))
        self.extra_allowed_paths = extra_allowed_paths or []

        # 在 relaxed 模式扩展允许的路径
        if security_level == SecurityLevel.RELAXED:
            self.forbidden_paths = []  # 不限制
        else:
            self.forbidden_paths = self.FORBIDDEN_PATHS.copy()

    @staticmethod
    def _normalize_posix_path(path: PurePosixPath) -> PurePosixPath:
        """规范化 POSIX 路径，解析 . 和 .. 组件（PurePosixPath 无 resolve 方法）"""
        parts = []
        for part in path.parts:
            if part in ('/', ''):
                continue
            elif part == '.':
                continue
            elif part == '..':
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        if not parts:
            return PurePosixPath('/')
        result = PurePosixPath('/')
        for part in parts:
            result = result / part
        return result

    def validate_path(self, user_path: str) -> PurePosixPath:
        """
        验证用户提供的路径
        
        Args:
            user_path: 用户提供的路径
            
        Returns:
            PurePosixPath: 验证后的安全路径
            
        Raises:
            SecurityError: 如果路径不安全
        """
        if not user_path or not user_path.strip():
            raise SecurityError("路径不能为空")

        # 转换为绝对路径（使用 PurePosixPath，因为路径是远程 Unix 路径）
        full_path = self._normalize_posix_path(self.base_dir / user_path)

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
    """从环境变量创建验证器实例

    支持的环境变量：
    - SSH_SECURITY_LEVEL: 安全级别 (strict/balanced/relaxed)
    - SSH_EXTRA_ALLOWED_COMMANDS: 逗号分隔的额外允许命令
    - SSH_ALLOWED_COMMANDS_FILE: JSON 白名单配置文件路径（优先级高于 SSH_EXTRA_ALLOWED_COMMANDS）
    - SSH_BASE_DIR: 基础目录
    """
    # 读取安全级别
    level_str = os.getenv('SSH_SECURITY_LEVEL', 'balanced').lower()
    try:
        security_level = SecurityLevel(level_str)
    except ValueError:
        security_level = SecurityLevel.BALANCED
        print(f"⚠️  未知的安全级别 '{level_str}'，使用默认值 'balanced'")

    # 读取额外允许的命令（两种方式：配置文件 > 环境变量）
    config_file = os.getenv('SSH_ALLOWED_COMMANDS_FILE', '')
    extra_commands: set[str] = set()

    if config_file and os.path.exists(config_file):
        # 方式 1：从 JSON 配置文件加载（结构化，推荐）
        try:
            command_validator = CommandValidator.from_config_file(
                config_file, security_level=security_level
            )
        except Exception as e:
            print(f"⚠️  加载白名单配置文件失败: {e}，回退到环境变量方式")
            command_validator = None
        else:
            # 同时读取环境变量中的额外命令，叠加到配置文件之上
            extra_commands_str = os.getenv('SSH_EXTRA_ALLOWED_COMMANDS', '')
            if extra_commands_str:
                extra_commands = set(cmd.strip() for cmd in extra_commands_str.split(',') if cmd.strip())
                command_validator.extra_allowed_commands |= extra_commands
                command_validator.allowed_commands = command_validator._build_allowed_commands()
    else:
        command_validator = None

    if command_validator is None:
        # 方式 2：从环境变量加载（简单，逗号分隔）
        extra_commands_str = os.getenv('SSH_EXTRA_ALLOWED_COMMANDS', '')
        if extra_commands_str:
            extra_commands = set(cmd.strip() for cmd in extra_commands_str.split(',') if cmd.strip())

        command_validator = CommandValidator(
            security_level=security_level,
            extra_allowed_commands=extra_commands
        )

    # 读取基础目录
    base_dir = os.getenv('SSH_BASE_DIR', '/home')

    path_validator = PathValidator(
        security_level=security_level,
        base_dir=base_dir
    )

    return command_validator, path_validator


# 创建全局实例
command_validator, path_validator = create_validators_from_env()
