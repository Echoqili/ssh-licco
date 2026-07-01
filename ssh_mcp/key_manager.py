from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa


@dataclass
class SSHKeyPair:
    private_key: str
    public_key: str
    key_type: str
    fingerprint: str
    comment: str | None = None


class KeyManager:
    def __init__(self, key_dir: Path | None = None):
        self.key_dir = key_dir or Path.home() / ".ssh"
        self.key_dir.mkdir(parents=True, exist_ok=True)

    def generate_rsa_key(self, key_size: int = 4096, comment: str | None = None) -> SSHKeyPair:
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )
        return self._serialize_key(private_key, "rsa", comment)

    def generate_ed25519_key(self, comment: str | None = None) -> SSHKeyPair:
        private_key = ed25519.Ed25519PrivateKey.generate()
        return self._serialize_key(private_key, "ed25519", comment)

    def _serialize_key(self, private_key, key_type: str, comment: str | None) -> SSHKeyPair:
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
        )

        fingerprint = self._get_fingerprint(public_ssh)

        return SSHKeyPair(
            private_key=private_pem.decode("utf-8"),
            public_key=public_ssh.decode("utf-8"),
            key_type=key_type,
            fingerprint=fingerprint,
            comment=comment,
        )

    def _get_fingerprint(self, public_key: bytes) -> str:
        import hashlib

        public_key_str = public_key.decode("utf-8")
        key_data = public_key_str.split()[1]
        import base64

        key_bytes = base64.b64decode(key_data)
        digest = hashlib.sha256(key_bytes).digest()
        return f"SHA256:{base64.b64encode(digest).decode('utf-8').rstrip('=')}"

    def load_key(self, private_key_path: Path, passphrase: str | None = None) -> SSHKeyPair:
        with open(private_key_path, "rb") as f:
            private_pem = f.read()

        if passphrase:
            passphrase_bytes = passphrase.encode("utf-8")
        else:
            passphrase_bytes = None

        # 密钥可能以 OpenSSH 格式 (-----BEGIN OPENSSH PRIVATE KEY-----) 或传统 PEM 格式保存
        # load_ssh_private_key 支持 OpenSSH 格式 (cryptography >= 3.1)
        # load_pem_private_key 支持传统 PKCS 格式
        private_key = None
        if hasattr(serialization, "load_ssh_private_key"):
            try:
                private_key = serialization.load_ssh_private_key(
                    private_pem, password=passphrase_bytes, backend=default_backend()
                )
            except (ValueError, TypeError):
                pass  # 不是 OpenSSH 格式，尝试传统 PEM

        if private_key is None:
            private_key = serialization.load_pem_private_key(
                private_pem, password=passphrase_bytes, backend=default_backend()
            )

        if isinstance(private_key, rsa.RSAPrivateKey):
            key_type = "rsa"
        elif isinstance(private_key, ed25519.Ed25519PrivateKey):
            key_type = "ed25519"
        else:
            key_type = "unknown"

        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
        )

        fingerprint = self._get_fingerprint(public_ssh)

        return SSHKeyPair(
            private_key=private_pem.decode("utf-8"),
            public_key=public_ssh.decode("utf-8"),
            key_type=key_type,
            fingerprint=fingerprint,
        )

    def load_key_from_str(self, private_key_pem: str, passphrase: str | None = None) -> SSHKeyPair:
        """从内存字符串加载私钥，不接触磁盘。

        用于「密钥不落地」加固场景：私钥由 SecretProvider 从 KMS 临时拉取到内存，
        通过本方法解析为 SSHKeyPair，用完即由调用方清零。

        Args:
            private_key_pem: PEM 格式私钥字符串
            passphrase: 私钥口令（可选）
        """
        private_pem = private_key_pem.encode("utf-8")
        passphrase_bytes = passphrase.encode("utf-8") if passphrase else None

        private_key = None
        if hasattr(serialization, "load_ssh_private_key"):
            try:
                private_key = serialization.load_ssh_private_key(
                    private_pem, password=passphrase_bytes, backend=default_backend()
                )
            except (ValueError, TypeError):
                pass

        if private_key is None:
            private_key = serialization.load_pem_private_key(
                private_pem, password=passphrase_bytes, backend=default_backend()
            )

        if isinstance(private_key, rsa.RSAPrivateKey):
            key_type = "rsa"
        elif isinstance(private_key, ed25519.Ed25519PrivateKey):
            key_type = "ed25519"
        else:
            key_type = "unknown"

        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
        )
        fingerprint = self._get_fingerprint(public_ssh)

        return SSHKeyPair(
            private_key=private_key_pem,  # 调用方负责清零原始字符串
            public_key=public_ssh.decode("utf-8"),
            key_type=key_type,
            fingerprint=fingerprint,
        )

    def save_key(self, key_pair: SSHKeyPair, private_key_path: Path) -> None:
        # 加固点 2：密钥不落地磁盘
        # 当 SSH_SECRET_PROVIDER_ENABLED=true 时，禁止把私钥写入磁盘。
        from .secret_provider import is_secret_provider_enabled

        if is_secret_provider_enabled():
            raise PermissionError(
                "密钥不落地模式已启用（SSH_SECRET_PROVIDER_ENABLED=true），"
                "禁止将私钥写入磁盘。私钥应通过 SecretProvider 临时拉取到内存使用。"
            )
        private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(private_key_path, "w") as f:
            f.write(key_pair.private_key)
        os.chmod(private_key_path, 0o600)

        public_key_path = private_key_path.with_suffix(".pub")
        with open(public_key_path, "w") as f:
            f.write(key_pair.public_key)
