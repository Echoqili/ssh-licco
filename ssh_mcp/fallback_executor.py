from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from typing import Optional

from .connection_config import ConnectionConfig


class FallbackExecutor:
    """远程命令执行器，带自动降级优先级

    优先级链:
        1️⃣ MCP 工具 (外部使用)
        2️⃣ CLI (ssh-licco exec) — 通过 subprocess 调用
        3️⃣ Paramiko — 直接 Python SSH 调用

    MCP 工具是最高优先级，由 AI 在外部判断是否可用。
    本执行器负责 2️⃣ → 3️⃣ 的自动降级。
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._cli_checked = False
        self._cli_available = False

    def check_cli_available(self) -> bool:
        if self._cli_checked:
            return self._cli_available
        try:
            result = subprocess.run(
                ["ssh-licco", "--version"],
                capture_output=True, text=True, timeout=10,
                shell=(sys.platform == "win32")
            )
            self._cli_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._cli_available = False
        self._cli_checked = True
        return self._cli_available

    def execute(self, command: str, timeout: Optional[int] = None) -> dict:
        """执行远程命令，自动选择最优方法

        Args:
            command: 要执行的命令
            timeout: 超时秒数

        Returns:
            dict: {"stdout": str, "stderr": str, "exit_code": int, "method": str}
        """
        if self.check_cli_available():
            return self._exec_via_cli(command, timeout)
        return self._exec_via_paramiko(command, timeout)

    def _exec_via_cli(self, command: str, timeout: Optional[int] = None) -> dict:
        env = os.environ.copy()
        env["SSH_SECURITY_LEVEL"] = "relaxed"
        env["SSH_EXTRA_ALLOWED_COMMANDS"] = "git,pip,npm,docker,pg_isready,psql,sh,bash,echo,cat,ls,whoami,hostname,uname,apt,sudo,systemctl,service,grep,find,sed,awk,tar,gzip,zip,wget,curl,make,cmake,gcc,g++,node,python,python3,java,mvn,gradle"
        env["SSH_HOST"] = self.config.host or ""
        env["SSH_USER"] = self.config.username or ""
        if self.config.password:
            env["SSH_PASSWORD"] = self.config.password
        env["SSH_PORT"] = str(self.config.port or 22)
        env["SSH_TIMEOUT"] = str(self.config.timeout or 60)

        if self.config.keepalive_interval:
            env["SSH_KEEPALIVE_INTERVAL"] = str(self.config.keepalive_interval)
        if hasattr(self.config, 'session_timeout') and self.config.session_timeout:
            env["SSH_SESSION_TIMEOUT"] = str(self.config.session_timeout)

        cmd = ["ssh-licco", "exec", "--", command]
        try:
            result = subprocess.run(
                cmd, env=env,
                capture_output=True, text=True,
                timeout=timeout or 60,
                shell=(sys.platform == "win32")
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "method": "cli"
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timed out after {} seconds".format(timeout or 60),
                "exit_code": -1,
                "method": "cli"
            }
        except FileNotFoundError:
            self._cli_available = False
            return self._exec_via_paramiko(command, timeout)
        except Exception as e:
            return {
                "stdout": "",
                "stderr": "CLI execution failed: {}".format(e),
                "exit_code": -1,
                "method": "cli"
            }

    def _exec_via_paramiko(self, command: str, timeout: Optional[int] = None) -> dict:
        try:
            from .session_manager import SSHSession

            async def _run():
                session = SSHSession(self.config)
                try:
                    await session.connect()
                    result = await session.execute_command(command, timeout=timeout or 60)
                    return {
                        "stdout": result.get("stdout", ""),
                        "stderr": result.get("stderr", ""),
                        "exit_code": result.get("exit_code", 0),
                        "method": "paramiko"
                    }
                finally:
                    try:
                        await session.disconnect()
                    except Exception:
                        pass

            try:
                return asyncio.run(_run())
            except RuntimeError:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(_run())
        except Exception as e:
            return {
                "stdout": "",
                "stderr": "Paramiko execution failed: {}".format(e),
                "exit_code": -1,
                "method": "paramiko"
            }

    @staticmethod
    def format_result(result: dict) -> str:
        """格式化执行结果为可读文本"""
        lines = []
        if result.get("stdout"):
            lines.append(result["stdout"])
        if result.get("stderr"):
            lines.append("[stderr] {}".format(result["stderr"]))
        lines.append("")
        lines.append("--- exit_code: {} | method: {} ---".format(
            result.get("exit_code", -1), result.get("method", "unknown")
        ))
        return "\n".join(lines)


def create_fallback_executor_from_env() -> FallbackExecutor:
    """从环境变量创建 FallbackExecutor 实例"""
    password = os.getenv("SSH_PASSWORD", "")
    if not password:
        print("Error: SSH_PASSWORD not set", file=sys.stderr)
        sys.exit(1)

    config = ConnectionConfig(
        host=os.getenv("SSH_HOST", ""),
        port=int(os.getenv("SSH_PORT", "22")),
        username=os.getenv("SSH_USER", "root"),
        password=password,
        auth_method="password",
        timeout=int(os.getenv("SSH_TIMEOUT", "60")),
        keepalive_interval=int(os.getenv("SSH_KEEPALIVE_INTERVAL", "30")),
        strict_host_key_checking=False,
        accept_new_host_key=True,
    )
    return FallbackExecutor(config)