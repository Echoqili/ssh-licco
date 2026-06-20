#!/usr/bin/env python3
"""Version sync script - updates version in all project files.

Usage:
    python sync_version.py x.x.x

This script updates the version in:
    - ssh_mcp/__init__.py   (__version__ and comment)
    - pyproject.toml        (version field)
    - VERSION               (plain text)
    - package.json          (version field)

After version files are updated, it also runs scripts/sync_docs.py
to synchronize version info and test statistics in documentation.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

FILES = {
    "ssh_mcp/__init__.py": {
        "type": "init",
        "patterns": [
            (r'# 版本号：[\d.]+', '# 版本号：{version}'),
            (r'__version__ = "[\d.]+"', '__version__ = "{version}"'),
        ],
    },
    "pyproject.toml": {
        "type": "toml",
        "patterns": [
            (r'^version = "[\d.]+"', 'version = "{version}"'),
        ],
    },
    "VERSION": {
        "type": "version",
    },
    "package.json": {
        "type": "json",
        "key": "version",
    },
}


def update_init(filepath: Path, version: str) -> bool:
    text = filepath.read_text(encoding="utf-8")
    for pattern, template in FILES["ssh_mcp/__init__.py"]["patterns"]:
        replacement = template.format(version=version)
        text, n = re.subn(pattern, replacement, text)
        if n == 0:
            print(f"  [WARN] Pattern not found: {pattern}")
        elif n > 1:
            print(f"  [WARN] Multiple matches ({n}) for pattern: {pattern}")
    filepath.write_text(text, encoding="utf-8")
    return True


def update_toml(filepath: Path, version: str) -> bool:
    text = filepath.read_text(encoding="utf-8")
    pattern, template = FILES["pyproject.toml"]["patterns"][0]
    replacement = template.format(version=version)
    text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if n == 0:
        print(f"  [WARN] Pattern not found: {pattern}")
        return False
    filepath.write_text(text, encoding="utf-8")
    return True


def update_json(filepath: Path, version: str, key: str) -> bool:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if key not in data:
        print(f"  [WARN] Key '{key}' not found in {filepath.name}")
        return False
    data[key] = version
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def update_plain(filepath: Path, version: str) -> bool:
    filepath.write_text(version + "\n", encoding="utf-8")
    return True


def sync_version(version: str) -> bool:
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"[ERROR] Invalid version format: {version!r} (expected x.y.z)")
        return False

    all_ok = True

    # 1. ssh_mcp/__init__.py
    path = ROOT / "ssh_mcp" / "__init__.py"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_init(path, version)

    # 2. pyproject.toml
    path = ROOT / "pyproject.toml"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_toml(path, version)

    # 3. VERSION
    path = ROOT / "VERSION"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_plain(path, version)

    # 4. package.json
    path = ROOT / "package.json"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_json(path, version, "version")

    if all_ok:
        print(f"\n[OK] All version files updated to {version}")
    else:
        print(f"\n[WARN] Some files had issues (see above)")
    return all_ok


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    version = sys.argv[1].strip()
    success = sync_version(version)
    if not success:
        sys.exit(1)

    # 同步文档中的版本号和测试统计
    print("\nSyncing documentation ...")
    docs_script = ROOT / "scripts" / "sync_docs.py"
    if docs_script.exists():
        result = subprocess.run(
            [sys.executable, str(docs_script)],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print("[WARN] Documentation sync failed")
            sys.exit(1)
    else:
        print(f"[WARN] Docs sync script not found: {docs_script}")

    sys.exit(0)


if __name__ == "__main__":
    main()