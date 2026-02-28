from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.backends import default_backend


@dataclass
class SSHKeyPair:
    private_key: str
    public_key: str
    key_type: str
    fingerprint: str
    comment: Optional[str] = None


class KeyManager:
    def __init__(self, key_dir: Optional[Path] = None):
        self.key_dir = key_dir or Path.home() / ".ssh"
        self.key_dir.mkdir(parents=True, exist_ok=True)

    def generate_rsa_key(self, key_size: int = 4096, comment: Optional[str] = None) -> SSHKeyPair:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        return self._serialize_key(private_key, "rsa", comment)

    def generate_ed25519_key(self, comment: Optional[str] = None) -> SSHKeyPair:
        private_key = ed25519.Ed25519PrivateKey.generate()
        return self._serialize_key(private_key, "ed25519", comment)

    def _serialize_key(self, private_key, key_type: str, comment: Optional[str]) -> SSHKeyPair:
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        
        fingerprint = self._get_fingerprint(public_ssh)
        
        return SSHKeyPair(
            private_key=private_pem.decode('utf-8'),
            public_key=public_ssh.decode('utf-8'),
            key_type=key_type,
            fingerprint=fingerprint,
            comment=comment
        )

    def _get_fingerprint(self, public_key: bytes) -> str:
        from cryptography.hazmat.primitives import hashes
        import hashlib
        
        public_key_str = public_key.decode('utf-8')
        key_data = public_key_str.split()[1]
        import base64
        key_bytes = base64.b64decode(key_data)
        digest = hashlib.sha256(key_bytes).digest()
        return f"SHA256:{base64.b64encode(digest).decode('utf-8').rstrip('=')}"

    def load_key(self, private_key_path: Path, passphrase: Optional[str] = None) -> SSHKeyPair:
        with open(private_key_path, 'rb') as f:
            private_pem = f.read()
        
        if passphrase:
            passphrase_bytes = passphrase.encode('utf-8')
        else:
            passphrase_bytes = None
            
        private_key = serialization.load_pem_private_key(
            private_pem,
            password=passphrase_bytes,
            backend=default_backend()
        )
        
        if isinstance(private_key, rsa.RSAPrivateKey):
            key_type = "rsa"
        elif isinstance(private_key, ed25519.Ed25519PrivateKey):
            key_type = "ed25519"
        else:
            key_type = "unknown"
        
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        
        fingerprint = self._get_fingerprint(public_ssh)
        
        return SSHKeyPair(
            private_key=private_pem.decode('utf-8'),
            public_key=public_ssh.decode('utf-8'),
            key_type=key_type,
            fingerprint=fingerprint
        )

    def save_key(self, key_pair: SSHKeyPair, private_key_path: Path) -> None:
        private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(private_key_path, 'w') as f:
            f.write(key_pair.private_key)
        os.chmod(private_key_path, 0o600)
        
        public_key_path = private_key_path.with_suffix('.pub')
        with open(public_key_path, 'w') as f:
            f.write(key_pair.public_key)
