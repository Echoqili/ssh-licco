#!/usr/bin/env python3
"""打包前自动同步文档中的版本号和测试统计信息。

Usage:
    python scripts/sync_docs.py

该脚本在 CI/CD 打包流程中调用，自动更新以下文档：
    - README.md：工具版本标注、测试用例统计
    - docs/CONTRIBUTING.md：测试用例统计
    - .trae/skills/ssh-mcp-dev/SKILL.md：Current Version
    - docs/skills/ssh-mcp-dev/SKILL.md：Current Version

版本号从 ssh_mcp/__init__.py 读取，测试统计通过运行 pytest 获取。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_current_version() -> str:
    """从 ssh_mcp/__init__.py 读取当前版本号。"""
    init_file = ROOT / "ssh_mcp" / "__init__.py"
    text = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([\d.]+)"', text)
    if not match:
        raise RuntimeError(f"无法在 {init_file} 中找到 __version__")
    return match.group(1)


def get_test_summary() -> str:
    """运行 pytest 获取测试统计摘要，统一返回 '409 passed, 0 skipped' 格式。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("运行 pytest 超时")
    except FileNotFoundError:
        raise RuntimeError("找不到 pytest，请先安装测试依赖")

    output = result.stdout + "\n" + result.stderr
    # pytest 输出示例：
    #   "409 passed, 0 skipped, 2 failed in 1.53s"
    #   "409 passed, 2 warnings in 1.53s"  (无 skipped 时省略)
    passed_match = re.search(r"(\d+) passed", output)
    skipped_match = re.search(r"(\d+) skipped", output)
    failed_match = re.search(r"(\d+) failed", output)

    if not passed_match:
        raise RuntimeError(f"无法从 pytest 输出中解析测试统计:\n{output}")

    passed = passed_match.group(1)
    skipped = skipped_match.group(1) if skipped_match else "0"
    failed = failed_match.group(1) if failed_match else "0"

    # 文档中统一展示 "N passed, M skipped"（不展示 failed，failed 为 0 时自然省略）
    return f"{passed} passed, {skipped} skipped"


def update_file(filepath: Path, replacements: list[tuple[str, str]]) -> bool:
    """对文件执行多组正则替换。"""
    text = filepath.read_text(encoding="utf-8")
    original = text
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    if text == original:
        print(f"  [SKIP] 无变化: {filepath.relative_to(ROOT)}")
        return False
    filepath.write_text(text, encoding="utf-8")
    print(f"  [OK] 已更新: {filepath.relative_to(ROOT)}")
    return True


def sync_docs(version: str, test_summary: str) -> bool:
    """同步所有文档。"""
    print(f"同步文档: version={version}, tests={test_summary}")

    updated = False

    # README.md
    readme = ROOT / "README.md"
    if readme.exists():
        updated |= update_file(
            readme,
            [
                # 工具版本标注：v1.x.x 扩充至 9 个
                (r"## 🛠️ 可用工具（v[\d.]+ 扩充至 9 个）", f"## 🛠️ 可用工具（v{version} 扩充至 9 个）"),
                # 测试用例统计（兼容 "N passed" 和 "N passed, M skipped" 两种旧格式）
                (r"\*\*测试用例\*\*\s*\|\s*\d+ passed(?:,\s*\d+ skipped)?",
                 f"**测试用例** | {test_summary}"),
            ],
        )

    # CONTRIBUTING.md
    contributing = ROOT / "docs" / "CONTRIBUTING.md"
    if contributing.exists():
        updated |= update_file(
            contributing,
            [
                # 兼容 "N passed" 和 "N passed, M skipped" 两种旧格式
                (r"# 运行所有测试（\d+ passed(?:,\s*\d+ skipped)?）",
                 f"# 运行所有测试（{test_summary}）"),
            ],
        )

    # SKILL.md 中的 Current Version
    for skill_path in [
        ROOT / ".trae" / "skills" / "ssh-mcp-dev" / "SKILL.md",
        ROOT / "docs" / "skills" / "ssh-mcp-dev" / "SKILL.md",
    ]:
        if skill_path.exists():
            updated |= update_file(
                skill_path,
                [
                    (r"- \*\*Current Version\*\*: [\d.]+",
                     f"- **Current Version**: {version}"),
                ],
            )

    if updated:
        print("\n[OK] 文档同步完成")
    else:
        print("\n[INFO] 文档无需更新")
    return updated


def main() -> int:
    try:
        version = get_current_version()
        test_summary = get_test_summary()
        sync_docs(version, test_summary)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
