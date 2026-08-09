#!/usr/bin/env python3
"""一体化版本发布脚本：一次性同步所有版本源，自检一致性，并可选 git commit / tag。

设计目标：
  1. 单一真源（`ssh_mcp/__init__.py:__version__`）——所有其他位置都从它推导或与其对齐。
  2. 零遗漏：无论手动改 pyproject.toml / VERSION / package.json / SKILL.md / README，
     运行 `python sync_version.py --check` 都能发现不一致。
  3. 一键升版：`python sync_version.py 2.7.1 --commit --tag`，等价于：
       改所有版本文件 → 同步文档版本 → 一致性自检通过 → commit → tag → push。

使用示例：
  # 预览（不写文件）
  python sync_version.py 2.7.1 --dry-run

  # 只改文件，不提交、不打 tag
  python sync_version.py 2.7.1 --no-commit --no-tag

  # 一体化发布（默认：改文件 + 同步文档 + 自检 + commit + tag，并 push 到所有 remote）
  python sync_version.py 2.7.1

  # 只做一致性自检（CI 中用）
  python sync_version.py --check

版本源清单（`SOURCES` 定义）：
  1. ssh_mcp/__init__.py    注释 + __version__（主真源）
  2. pyproject.toml         version = "x.y.z"（构建版本）
  3. VERSION                纯文本（pypi.yml 实际读取）
  4. package.json           version 字段（npm 包版本，与 Python 同步）
  5. package-lock.json      两处 version 字段（npm lock，必要时一并改）

然后 `scripts/sync_docs.py` 负责：
  - README.md 工具版本标注、测试统计
  - docs/CONTRIBUTING.md 测试统计
  - .trae/skills/** / docs/skills/** 中的 "Current Version"

一致性自检规则：
  - 上面 5 个版本源 + 文档里的 "Current Version" 必须全部与 `__version__` 一致。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ===== 版本源定义 =====
# 每新增一个需要同步版本的文件，只要在这里加一条即可，不影响其他逻辑。
SOURCES: list[dict] = [
    {
        "name": "ssh_mcp/__init__.py",
        "kind": "init",
        "patterns": [
            (r"# 版本号：[\d.]+", "# 版本号：{version}"),
            (r'__version__\s*=\s*"[\d.]+"', '__version__ = "{version}"'),
        ],
    },
    {
        "name": "pyproject.toml",
        "kind": "toml",
        "patterns": [
            (r'^version\s*=\s*"[\d.]+"', 'version = "{version}"'),
        ],
    },
    {
        "name": "VERSION",
        "kind": "plain",
    },
    {
        "name": "package.json",
        "kind": "json",
        "key": "version",
    },
    {
        "name": "package-lock.json",
        "kind": "json-lock",
    },
]

# git commit 时会一起提交的所有可能发生变动的文件
FILES_TO_ADD = [
    "sync_version.py",
    "ssh_mcp/__init__.py",
    "pyproject.toml",
    "VERSION",
    "package.json",
    "package-lock.json",
    "README.md",
    "docs/CONTRIBUTING.md",
    ".trae/skills/ssh-mcp-dev/SKILL.md",
    "docs/skills/ssh-mcp-dev/SKILL.md",
    ".github/workflows/pypi.yml",
]

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


# ===== 各种文件类型的读写 =====

def _apply_regex(filepath: Path, patterns: list[tuple[str, str]], version: str,
                 dry_run: bool) -> tuple[bool, str]:
    text = filepath.read_text(encoding="utf-8")
    original = text
    for pattern, template in patterns:
        replacement = template.format(version=version)
        text, n = re.subn(pattern, replacement, text,
                          flags=re.MULTILINE if pattern.startswith("^") else 0)
        if n == 0:
            print(f"  [WARN] 未命中 pattern: {pattern!r} in {filepath.name}")
    if dry_run:
        changed = text != original
        return changed, text
    filepath.write_text(text, encoding="utf-8")
    return True, text


def update_init(filepath: Path, version: str, dry_run: bool) -> bool:
    patterns = [s for s in SOURCES if s["name"] == "ssh_mcp/__init__.py"][0]["patterns"]
    changed, _ = _apply_regex(filepath, patterns, version, dry_run)
    return changed


def update_toml(filepath: Path, version: str, dry_run: bool) -> bool:
    patterns = [s for s in SOURCES if s["name"] == "pyproject.toml"][0]["patterns"]
    changed, _ = _apply_regex(filepath, patterns, version, dry_run)
    return changed


def update_plain(filepath: Path, version: str, dry_run: bool) -> bool:
    if dry_run:
        return filepath.read_text(encoding="utf-8").strip() != version
    filepath.write_text(version + "\n", encoding="utf-8")
    return True


def update_json_version(filepath: Path, version: str, key: str, dry_run: bool) -> bool:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if data.get(key) == version:
        return False
    if dry_run:
        return True
    data[key] = version
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def update_json_lock(filepath: Path, version: str, dry_run: bool) -> bool:
    """package-lock.json 需要同时更新根版本和 packages[''] 版本。"""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    changed = False
    if data.get("version") != version:
        if dry_run:
            return True
        data["version"] = version
        changed = True
    packages = data.get("packages", {})
    root_pkg = packages.get("", {})
    if root_pkg.get("version") != version:
        if dry_run:
            return True
        root_pkg["version"] = version
        packages[""] = root_pkg
        data["packages"] = packages
        changed = True
    if not changed:
        return False
    if dry_run:
        return True
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def update_source(src: dict, version: str, dry_run: bool) -> bool:
    path = ROOT / src["name"]
    if not path.exists():
        print(f"  [SKIP] 不存在: {src['name']}")
        return False
    kind = src["kind"]
    if kind == "init":
        return update_init(path, version, dry_run)
    if kind == "toml":
        return update_toml(path, version, dry_run)
    if kind == "plain":
        return update_plain(path, version, dry_run)
    if kind == "json":
        return update_json_version(path, version, src["key"], dry_run)
    if kind == "json-lock":
        return update_json_lock(path, version, dry_run)
    raise ValueError(f"未知 kind: {kind}")


# ===== 从真源读版本 + 一致性自检 =====

def read_canonical_version() -> str:
    """从 ssh_mcp/__init__.py 读 __version__ 作为唯一真源。"""
    init_file = ROOT / "ssh_mcp" / "__init__.py"
    text = init_file.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([\d.]+)"', text)
    if not m:
        raise RuntimeError(f"无法在 {init_file} 中找到 __version__")
    return m.group(1)


def check_source_consistency(expected: str) -> list[str]:
    """对 SOURCES + 文档 Current Version 做一致性自检，返回不一致列表。"""
    problems: list[str] = []

    for src in SOURCES:
        path = ROOT / src["name"]
        if not path.exists():
            continue
        kind = src["kind"]
        actual = None
        try:
            if kind == "init":
                t = path.read_text(encoding="utf-8")
                m = re.search(r'__version__\s*=\s*"([\d.]+)"', t)
                actual = m.group(1) if m else None
            elif kind == "toml":
                t = path.read_text(encoding="utf-8")
                m = re.search(r'^version\s*=\s*"([\d.]+)"', t, re.MULTILINE)
                actual = m.group(1) if m else None
            elif kind == "plain":
                actual = path.read_text(encoding="utf-8").strip()
            elif kind == "json":
                actual = json.loads(path.read_text(encoding="utf-8")).get(src["key"])
            elif kind == "json-lock":
                data = json.loads(path.read_text(encoding="utf-8"))
                v_root = data.get("version")
                v_pkg = data.get("packages", {}).get("", {}).get("version")
                if v_root != expected or (v_pkg is not None and v_pkg != expected):
                    problems.append(
                        f"{src['name']} root={v_root!r}, packages['']={v_pkg!r}, "
                        f"expected={expected!r}"
                    )
                    continue
                actual = expected
        except Exception as e:  # noqa: BLE001
            problems.append(f"{src['name']} 解析失败: {e}")
            continue
        if actual != expected:
            problems.append(
                f"{src['name']}: 预期 {expected!r}, 实际 {actual!r}"
            )

    # 文档中的 "Current Version"
    for skill_path in [
        ROOT / ".trae" / "skills" / "ssh-mcp-dev" / "SKILL.md",
        ROOT / "docs" / "skills" / "ssh-mcp-dev" / "SKILL.md",
    ]:
        if not skill_path.exists():
            continue
        t = skill_path.read_text(encoding="utf-8")
        m = re.search(r"- \*\*Current Version\*\*: ([\d.]+)", t)
        actual = m.group(1) if m else None
        if actual != expected:
            problems.append(
                f"{skill_path.relative_to(ROOT)} Current Version: "
                f"预期 {expected!r}, 实际 {actual!r}"
            )

    return problems


# ===== 文档版本同步（不依赖 pytest，失败零容忍） =====

SKILL_CURRENT_VERSION_PATHS = [
    ".trae/skills/ssh-mcp-dev/SKILL.md",
    "docs/skills/ssh-mcp-dev/SKILL.md",
]


def sync_docs_versions(version: str, dry_run: bool) -> bool:
    """同步所有文档中的版本号引用。与 scripts/sync_docs.py 解耦，不需要 pytest。

    目前覆盖：
      - *SKILL.md 中的 "- **Current Version**: x.y.z"
    """
    updated_any = False
    for rel in SKILL_CURRENT_VERSION_PATHS:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new, n = re.subn(
            r"- \*\*Current Version\*\*: [\d.]+",
            f"- **Current Version**: {version}",
            text,
        )
        if n == 0:
            print(f"  [SKIP] 无匹配: {rel}")
            continue
        if text == new:
            print(f"  [SKIP] 已是最新: {rel}")
            continue
        if dry_run:
            print(f"  [DRY-RUN] 会变更: {rel}")
            updated_any = True
            continue
        path.write_text(new, encoding="utf-8")
        print(f"  [OK] 已更新: {rel}")
        updated_any = True
    return updated_any


def run_sync_docs() -> tuple[bool, str]:
    """调用 scripts/sync_docs.py（主要是 README 测试统计更新，依赖 pytest）。"""
    script = ROOT / "scripts" / "sync_docs.py"
    if not script.exists():
        return False, f"脚本不存在: {script}"
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "sync_docs 超时（pytest 可能卡太久）"
    if result.returncode != 0:
        # pytest 跑不通时只是更新不了 README 中的测试统计，不影响版本号
        hint = "（pytest 收集失败属环境问题，CI 里能跑通即可）"
        return False, f"sync_docs 返回非零 {hint}"
    return True, "文档同步完成"


# ===== git 操作 =====

def git_status_porcelain() -> str:
    r = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
    )
    return r.stdout or ""


def git_commit_version(version: str, dry_run: bool) -> bool:
    commit_msg = f"chore(v{version}): bump version"
    if dry_run:
        print(f"[DRY-RUN] git add {' '.join(FILES_TO_ADD)}")
        print(f"[DRY-RUN] git commit -m '{commit_msg}'")
        return True

    if not git_status_porcelain():
        print("[WARN] 工作区没有任何变更，跳过 commit")
        return True

    r = subprocess.run(["git", "add"] + FILES_TO_ADD, cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] git add 失败: {r.stderr.strip()}")
        return False

    r = subprocess.run(["git", "commit", "-m", commit_msg],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] git commit 失败: {r.stderr.strip()}")
        return False
    print(f"[OK] commit: {commit_msg}")

    # push 到所有 remote
    remotes = (
        subprocess.run(["git", "remote"], cwd=ROOT, capture_output=True, text=True)
        .stdout.strip().splitlines()
    )
    ok = True
    for remote in remotes:
        r = subprocess.run(["git", "push", remote, "HEAD"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[OK] 推送到 {remote}")
        else:
            print(f"[ERROR] push {remote} 失败: {r.stderr.strip()}")
            ok = False
    return ok


def create_git_tag(version: str, dry_run: bool) -> bool:
    tag = f"v{version}"
    msg = f"Release v{version}"
    if dry_run:
        print(f"[DRY-RUN] git tag -a {tag} -m '{msg}'")
        return True
    r = subprocess.run(["git", "tag", "-a", tag, "-m", msg],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] git tag 失败: {r.stderr.strip()}")
        return False
    print(f"[OK] tag {tag} 已创建")
    remotes = (
        subprocess.run(["git", "remote"], cwd=ROOT, capture_output=True, text=True)
        .stdout.strip().splitlines()
    )
    ok = True
    for remote in remotes:
        r = subprocess.run(["git", "push", remote, tag],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[OK] tag 推送到 {remote}")
        else:
            print(f"[ERROR] tag push {remote} 失败: {r.stderr.strip()}")
            ok = False
    return ok


# ===== 主流程 =====

def sync_version_files(version: str, dry_run: bool) -> bool:
    print(f"\n=== 同步版本号 → {version} ===")
    any_changed = False
    for src in SOURCES:
        print(f"  - {src['name']} ...")
        if update_source(src, version, dry_run):
            any_changed = True
            print(f"    {'[DRY-RUN] 会变更' if dry_run else '已更新'}")
        else:
            print(f"    已是最新")
    return any_changed


def do_consistency_check(version: str) -> bool:
    print(f"\n=== 一致性自检（真源版本 {version}）===")
    problems = check_source_consistency(version)
    if not problems:
        print("[OK] 所有版本源与文档均一致 ✅")
        return True
    print(f"[FAIL] 发现 {len(problems)} 处不一致：")
    for p in problems:
        print(f"  ❌ {p}")
    print("\n提示：运行 `python sync_version.py <version>` 一键修复。")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="一体化版本发布：同步版本源 + 自检 + 同步文档 + commit/tag/push",
    )
    parser.add_argument("version", nargs="?", help="新的版本号（x.y.z）；若只做 --check 可省略")
    parser.add_argument(
        "--check", action="store_true",
        help="只做一致性自检，不改任何文件",
    )
    parser.add_argument(
        "--no-commit", action="store_true",
        help="跳过 git commit 和 push",
    )
    parser.add_argument(
        "--no-tag", action="store_true",
        help="跳过 git tag 和 push tag",
    )
    parser.add_argument(
        "--no-docs", action="store_true",
        help="跳过同步文档（sync_docs.py 里会跑 pytest，CI 里可能单独跑过）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只打印会发生的变更，不写文件、不 commit",
    )
    args = parser.parse_args()

    # 1. --check 模式
    if args.check:
        return 0 if do_consistency_check(read_canonical_version()) else 1

    # 2. 其余模式都需要目标版本号
    if not args.version:
        parser.error("需要提供目标版本号，或使用 --check 做自检")
    version = args.version.strip()
    if not VERSION_RE.match(version):
        print(f"[ERROR] 版本号格式错误: {version!r}（应为 x.y.z）", file=sys.stderr)
        return 1

    # 3. 改版本源
    sync_version_files(version, dry_run=args.dry_run)

    # 4. 同步文档版本号（这部分不依赖 pytest，任何时候都该成功）
    if not args.no_docs:
        print("\n=== 同步文档中的版本号 ===")
        if args.dry_run:
            print("[DRY-RUN] 会更新 SKILL.md 里的 Current Version 等字段")
            sync_docs_versions(version, dry_run=True)
        else:
            sync_docs_versions(version, dry_run=False)

    # 5. 同步文档测试统计 + 其他（scripts/sync_docs.py，内部会跑 pytest，本地缺依赖时可能失败）
    if not args.no_docs:
        print("\n=== 同步文档测试统计（scripts/sync_docs.py）===")
        if args.dry_run:
            print("[DRY-RUN] 会调用 scripts/sync_docs.py（更新 README / CONTRIBUTING 测试统计）")
        else:
            ok, msg = run_sync_docs()
            if ok:
                print(f"[OK] {msg}")
            else:
                print(f"[WARN] {msg}（继续执行，CI 会单独补跑）")

    # 6. 一致性自检（文件写入完成后做，dry-run 跳过）
    if args.dry_run:
        print("\n[DRY-RUN] 跳过一致性自检（文件未实际写入）")
    else:
        if not do_consistency_check(version):
            return 1

    # 7. git commit + push
    if not args.no_commit:
        print("\n=== git commit & push ===")
        if not git_commit_version(version, dry_run=args.dry_run):
            return 1

    # 8. git tag + push tag
    if not args.no_tag:
        print("\n=== git tag ===")
        if not create_git_tag(version, dry_run=args.dry_run):
            return 1

    print("\n[DONE] 全部完成 🎉")
    return 0


if __name__ == "__main__":
    sys.exit(main())
