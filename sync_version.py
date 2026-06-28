#!/usr/bin/env python3
"""Version sync script - updates version in all project files.

Usage:
    python sync_version.py x.x.x [--tag] [--dry-run]

This script updates the version in:
    - ssh_mcp/__init__.py   (__version__ and comment)
    - pyproject.toml        (version field)
    - VERSION               (plain text)

After version files are updated, it also runs scripts/sync_docs.py
to synchronize version info and test statistics in documentation.

Options:
    --tag        Create an annotated git tag and push to all remotes
    --dry-run    Show what would be changed without writing files
"""

import argparse
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
}


def update_init(filepath: Path, version: str, dry_run: bool = False) -> bool:
    text = filepath.read_text(encoding="utf-8")
    for pattern, template in FILES["ssh_mcp/__init__.py"]["patterns"]:
        replacement = template.format(version=version)
        text, n = re.subn(pattern, replacement, text)
        if n == 0:
            print(f"  [WARN] Pattern not found: {pattern}")
        elif n > 1:
            print(f"  [WARN] Multiple matches ({n}) for pattern: {pattern}")
    if dry_run:
        print(f"  [DRY-RUN] Would update {filepath.relative_to(ROOT)}")
        return True
    filepath.write_text(text, encoding="utf-8")
    return True


def update_toml(filepath: Path, version: str, dry_run: bool = False) -> bool:
    text = filepath.read_text(encoding="utf-8")
    pattern, template = FILES["pyproject.toml"]["patterns"][0]
    replacement = template.format(version=version)
    text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if n == 0:
        print(f"  [WARN] Pattern not found: {pattern}")
        return False
    if dry_run:
        print(f"  [DRY-RUN] Would update {filepath.relative_to(ROOT)}")
        return True
    filepath.write_text(text, encoding="utf-8")
    return True


def update_json(filepath: Path, version: str, key: str, dry_run: bool = False) -> bool:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if key not in data:
        print(f"  [WARN] Key '{key}' not found in {filepath.name}")
        return False
    if dry_run:
        print(f"  [DRY-RUN] Would update {filepath.relative_to(ROOT)} ({key}: {data[key]} -> {version})")
        return True
    data[key] = version
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def update_plain(filepath: Path, version: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"  [DRY-RUN] Would update {filepath.relative_to(ROOT)}")
        return True
    filepath.write_text(version + "\n", encoding="utf-8")
    return True


def create_git_tag(version: str, dry_run: bool = False) -> bool:
    """创建 annotated git tag 并推送到所有远程仓库。"""
    tag_name = f"v{version}"
    tag_message = f"v{version}: release"

    if dry_run:
        print(f"[DRY-RUN] git tag -a {tag_name} -m '{tag_message}'")
        return True

    # 创建标签
    result = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", tag_message],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[ERROR] git tag failed: {result.stderr.strip()}")
        return False
    print(f"[OK] git tag {tag_name} created")

    # 推送到所有远程仓库
    remotes_result = subprocess.run(
        ["git", "remote"], cwd=ROOT, capture_output=True, text=True,
    )
    remotes = remotes_result.stdout.strip().splitlines()
    if not remotes:
        print("[WARN] No git remotes configured, tag created locally only")
        return True

    all_ok = True
    for remote in remotes:
        push_result = subprocess.run(
            ["git", "push", remote, tag_name],
            cwd=ROOT, capture_output=True, text=True,
        )
        if push_result.returncode == 0:
            print(f"[OK] Tag {tag_name} pushed to {remote}")
        else:
            print(f"[ERROR] Push to {remote} failed: {push_result.stderr.strip()}")
            all_ok = False

    return all_ok


def sync_version(version: str, dry_run: bool = False) -> bool:
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"[ERROR] Invalid version format: {version!r} (expected x.y.z)")
        return False

    all_ok = True

    # 1. ssh_mcp/__init__.py
    path = ROOT / "ssh_mcp" / "__init__.py"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_init(path, version, dry_run)

    # 2. pyproject.toml
    path = ROOT / "pyproject.toml"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_toml(path, version, dry_run)

    # 3. VERSION
    path = ROOT / "VERSION"
    print(f"Updating {path.relative_to(ROOT)} ...")
    all_ok &= update_plain(path, version, dry_run)

    if all_ok:
        print(f"\n[OK] All version files updated to {version}")
    else:
        print(f"\n[WARN] Some files had issues (see above)")
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Sync version across all project files and optionally create git tag.",
        epilog="Example: python sync_version.py 1.6.3 --tag",
    )
    parser.add_argument("version", help="Version number in x.y.z format")
    parser.add_argument(
        "--tag", action="store_true",
        help="Create an annotated git tag and push to all remotes",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be changed without writing files",
    )
    args = parser.parse_args()

    version = args.version.strip()
    success = sync_version(version, dry_run=args.dry_run)
    if not success:
        sys.exit(1)

    # 同步文档中的版本号和测试统计
    if not args.dry_run:
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

    # 创建并推送 git tag
    if args.tag:
        print("\nCreating git tag ...")
        if not create_git_tag(version, dry_run=args.dry_run):
            print("[WARN] Git tag creation/push failed")
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()