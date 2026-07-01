"""SSH-LICCO 凭证管理 — 加固点 2：密钥不落地磁盘

生产跳板机托管的服务器私钥，不能以明文文件形式持久保存在跳板机磁盘上。
本模块提供 SecretProvider 抽象 + 多种后端实现，从外部密钥管理服务（KMS）临时
拉取私钥到内存中使用，进程退出（或连接关闭）时立即清理：

  ┌──────────────┐     fetch-on-demand      ┌────────────────┐
  │  ssh-licco   │ ───────────────────────▶ │ KMS / Vault /  │
  │  (in memory) │ ◀─────────────────────── │  env-injected  │
  └──────────────┘   私钥仅存于进程内存      └────────────────┘
        │
        │  atexit / session close
        ▼
    立即清零内存中的私钥字节

支持的后端（通过环境变量 SSH_SECRET_PROVIDER 选择）：

  - env     : 私钥直接从环境变量读取（开发/CI 用，仍不落盘）
              SSH_SECRET_ENV_KEY_<NAME> 指定每个连接的私钥环境变量名
  - command : 执行外部命令（如 vault kv get / aws secretsmanager get）拉取私钥
              SSH_SECRET_COMMAND_<NAME> 指定命令，stdout 即私钥内容
  - http    : 从 HTTP(S) 接口拉取，请求头携带 SSH_SECRET_HTTP_TOKEN
              SSH_SECRET_HTTP_URL_<NAME> / SSH_SECRET_HTTP_TOKEN 配置

设计原则：
  - 私钥内容绝不写入磁盘文件；KeyManager.save_key 在「密钥不落地」模式启用时
    会抛错，强制走内存路径。
  - 私钥字节在不再使用时显式清零（best-effort，Python 字符串不可变，但 bytes
    可通过 ctypes.memset 清零；这里用 bytearray + del 最大化清理效果）。
  - 临时凭证缓存仅存活于进程生命周期，atexit 钩子统一清理。
"""

from __future__ import annotations

import atexit
import os
import subprocess
import threading
import urllib.request
from dataclasses import dataclass


class SecretProviderError(RuntimeError):
    """凭证拉取失败"""


@dataclass
class SecretMaterial:
    """拉取到的凭证材料。使用完应调用 wipe() 清零。"""

    name: str  # 连接名 / 凭证标识
    data: bytearray  # 私钥内容（bytearray 便于清零）
    source: str  # 来源描述（env/command/http），便于审计

    def as_str(self) -> str:
        return self.data.decode("utf-8", errors="strict")

    def wipe(self) -> None:
        """清零内存中的私钥字节（best-effort）。"""
        for i in range(len(self.data)):
            self.data[i] = 0
        self.data.clear()


class SecretProvider:
    """凭证提供者抽象基类。子类实现 fetch()。"""

    def fetch(self, name: str) -> SecretMaterial:  # pragma: no cover - abstract
        raise NotImplementedError

    def close(self) -> None:
        """清理资源（如 HTTP keep-alive 连接）。默认无操作。"""


class EnvSecretProvider(SecretProvider):
    """从环境变量读取私钥。"""

    def fetch(self, name: str) -> SecretMaterial:
        var = os.getenv(f"SSH_SECRET_ENV_KEY_{name.upper()}") or os.getenv(
            f"SSH_SECRET_ENV_KEY_{name}"
        )
        if not var:
            # 兼容：直接以 name 作为变量名
            var = os.getenv(name)
        if not var:
            raise SecretProviderError(
                f"env provider: 私钥环境变量未配置（尝试过 SSH_SECRET_ENV_KEY_{name.upper()} / {name}）"
            )
        return SecretMaterial(name=name, data=bytearray(var.encode("utf-8")), source="env")


class CommandSecretProvider(SecretProvider):
    """执行外部命令拉取私钥。stdout 即私钥 PEM 内容。"""

    def fetch(self, name: str) -> SecretMaterial:
        cmd = os.getenv(f"SSH_SECRET_COMMAND_{name.upper()}") or os.getenv(
            f"SSH_SECRET_COMMAND_{name}"
        )
        if not cmd:
            raise SecretProviderError(f"command provider: 未配置 SSH_SECRET_COMMAND_{name.upper()}")
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                timeout=30,
                check=True,
                text=False,  # 拿 bytes 自行管理清零
            )
        except subprocess.CalledProcessError as e:
            raise SecretProviderError(
                f"command provider: 命令退出码 {e.returncode}: {e.stderr.decode('utf-8', 'replace')}"
            )
        except subprocess.TimeoutExpired:
            raise SecretProviderError("command provider: 拉取私钥命令超时（>30s）")
        return SecretMaterial(name=name, data=bytearray(proc.stdout), source="command")


class HttpSecretProvider(SecretProvider):
    """从 HTTP(S) 接口拉取私钥。"""

    def __init__(self):
        self._token = os.getenv("SSH_SECRET_HTTP_TOKEN", "")
        self._timeout = float(os.getenv("SSH_SECRET_HTTP_TIMEOUT", "15"))

    def fetch(self, name: str) -> SecretMaterial:
        url = os.getenv(f"SSH_SECRET_HTTP_URL_{name.upper()}") or os.getenv(
            f"SSH_SECRET_HTTP_URL_{name}"
        )
        if not url:
            raise SecretProviderError(f"http provider: 未配置 SSH_SECRET_HTTP_URL_{name.upper()}")
        req = urllib.request.Request(url)
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read()
        except Exception as e:
            raise SecretProviderError(f"http provider: 拉取 {name} 失败: {e}")
        return SecretMaterial(name=name, data=bytearray(body), source="http")


_PROVIDERS: dict[str, type[SecretProvider]] = {
    "env": EnvSecretProvider,
    "command": CommandSecretProvider,
    "http": HttpSecretProvider,
}


class SecretManager:
    """凭证管理器：单例，负责 provider 选择、内存缓存、atexit 清理。

    使用方式（在 ssh_connect 处理器中）：
        sm = SecretManager.instance()
        if sm.enabled:
            material = sm.fetch(host_name)        # 拉到内存
            try:
                pair = KeyManager().load_key_from_str(material.as_str())
                ...用 pair 建立 SSH 连接...
            finally:
                sm.release(material)              # 用完立即清零
    """

    _instance: SecretManager | None = None
    _lock = threading.Lock()

    def __init__(self):
        self.enabled = os.getenv("SSH_SECRET_PROVIDER_ENABLED", "false").lower() == "true"
        provider_kind = os.getenv("SSH_SECRET_PROVIDER", "env").lower()
        self._provider: SecretProvider | None = None
        if self.enabled:
            cls = _PROVIDERS.get(provider_kind)
            if cls is None:
                raise SecretProviderError(
                    f"未知的 SSH_SECRET_PROVIDER={provider_kind!r}，可选: {list(_PROVIDERS)}"
                )
            self._provider = cls()
            # 注册进程退出清理
            atexit.register(self.shutdown)
        # 当前进程持有的所有凭证材料（用于退出时统一清零）
        self._live: list[SecretMaterial] = []
        self._live_lock = threading.Lock()

    @classmethod
    def instance(cls) -> SecretManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def fetch(self, name: str) -> SecretMaterial:
        if not self.enabled or self._provider is None:
            raise SecretProviderError("secret manager 未启用（SSH_SECRET_PROVIDER_ENABLED=true）")
        material = self._provider.fetch(name)
        with self._live_lock:
            self._live.append(material)
        return material

    def release(self, material: SecretMaterial) -> None:
        """归还凭证：从 live 列表移除并清零。"""
        with self._live_lock:
            try:
                self._live.remove(material)
            except ValueError:
                pass
        material.wipe()

    def shutdown(self) -> None:
        """进程退出时统一清零所有未释放的凭证。"""
        with self._live_lock:
            for m in self._live:
                try:
                    m.wipe()
                except Exception:
                    pass
            self._live.clear()
        if self._provider is not None:
            try:
                self._provider.close()
            except Exception:
                pass


def is_secret_provider_enabled() -> bool:
    """便捷查询：是否启用了密钥不落地模式。"""
    return SecretManager.instance().enabled
