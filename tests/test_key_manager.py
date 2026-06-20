from __future__ import annotations

from pathlib import Path

import pytest

from ssh_mcp.key_manager import KeyManager, SSHKeyPair


class TestSSHKeyPair:
    def test_creation(self):
        kp = SSHKeyPair(
            private_key="priv",
            public_key="pub",
            key_type="rsa",
            fingerprint="SHA256:abc",
            comment="test",
        )
        assert kp.private_key == "priv"
        assert kp.public_key == "pub"
        assert kp.key_type == "rsa"
        assert kp.comment == "test"

    def test_default_comment(self):
        kp = SSHKeyPair(
            private_key="priv",
            public_key="pub",
            key_type="ed25519",
            fingerprint="SHA256:abc",
        )
        assert kp.comment is None


class TestKeyManager:
    def test_generate_ed25519_key(self, tmp_path):
        km = KeyManager(key_dir=tmp_path)
        key_pair = km.generate_ed25519_key(comment="test")
        assert key_pair.key_type == "ed25519"
        assert "ssh-ed25519" in key_pair.public_key
        assert key_pair.fingerprint.startswith("SHA256:")
        assert key_pair.comment == "test"

    def test_generate_rsa_key(self, tmp_path):
        km = KeyManager(key_dir=tmp_path)
        key_pair = km.generate_rsa_key(key_size=2048, comment="test-rsa")
        assert key_pair.key_type == "rsa"
        assert "ssh-rsa" in key_pair.public_key
        assert key_pair.fingerprint.startswith("SHA256:")

    def test_save_and_load_key(self, tmp_path):
        km = KeyManager(key_dir=tmp_path)
        key_pair = km.generate_ed25519_key(comment="test-save")

        key_path = tmp_path / "test_key"
        km.save_key(key_pair, key_path)

        assert key_path.exists()
        assert key_path.with_suffix(".pub").exists()

        # load_key 现在优先尝试 load_ssh_private_key (OpenSSH 格式)，
        # 再回退到 load_pem_private_key (传统 PEM 格式)
        loaded = km.load_key(key_path)
        assert loaded.key_type == "ed25519"
        assert loaded.fingerprint == key_pair.fingerprint

    def test_key_dir_created(self, tmp_path):
        key_dir = tmp_path / "new_dir"
        km = KeyManager(key_dir=key_dir)
        assert key_dir.exists()

    def test_save_key_creates_parent_dirs(self, tmp_path):
        km = KeyManager(key_dir=tmp_path)
        key_pair = km.generate_ed25519_key()
        key_path = tmp_path / "sub" / "dir" / "key"
        km.save_key(key_pair, key_path)
        assert key_path.exists()
