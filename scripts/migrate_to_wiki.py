#!/usr/bin/env python3
"""Migrate and organize project documentation to GitHub Wiki."""

import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(r"D:\pyworkplace\ssh-mcp")
WIKI_DIR = Path(r"D:\pyworkplace\ssh-licco-wiki")
WIKI_BASE_PATH = "/Echoqili/ssh-licco/wiki"

# Mapping from source file (relative to project root) to wiki page name
PAGE_MAP = {
    "README.md": "Home.md",
    "MCP_CONFIG_GUIDE.md": "MCP-Config-Guide.md",
    "SECURITY_CONFIG_GUIDE.md": "Security-Config-Guide.md",
    "SECURITY_QUICK_CONFIG.md": "Security-Quick-Config.md",
    "SECURITY_SCORE_SUMMARY.md": "Security-Score-Summary.md",
    "CHANGELOG.md": "Changelog.md",
    "DEVLOG.md": "Devlog.md",
    "LESSON.md": "Lessons.md",
    "docs/API_REFERENCE.md": "API-Reference.md",
    "docs/CONTRIBUTING.md": "Contributing.md",
    "docs/OPENSPEC_GUIDE.md": "OpenSpec-Guide.md",
    "docs/skills/RELEASE_SKILL.md": "Skills-Release.md",
    "docs/skills/GIT_WORKFLOW_SKILL.md": "Skills-Git-Workflow.md",
    "docs/skills/OPENSPEC_WORKFLOW_SKILL.md": "Skills-OpenSpec-Workflow.md",
    "docs/skills/ssh-mcp-dev/SKILL.md": "Skills-SSH-MCP-Dev.md",
    "docs/skills/ssh-mcp-ops/SKILL.md": "Skills-SSH-MCP-Ops.md",
    "docs/skills/ssh-mcp-setup/SKILL.md": "Skills-SSH-MCP-Setup.md",
    "docs/skills/ssh-mcp-troubleshoot/SKILL.md": "Skills-SSH-MCP-Troubleshoot.md",
    "config/README.md": "Config-README.md",
    "config/CONFIG_GUIDE.md": "Config-Guide.md",
}

# Additional link aliases used inside markdown files (relative paths in sub-docs)
LINK_ALIASES = {
    "../README.md": "Home",
    "ssh-mcp-dev/SKILL.md": "Skills-SSH-MCP-Dev",
    "RELEASE_SKILL.md": "Skills-Release",
    "ssh-mcp-ops/SKILL.md": "Skills-SSH-MCP-Ops",
    "../OPENSPEC_GUIDE.md": "OpenSpec-Guide",
    "OPENSPEC_GUIDE.md": "OpenSpec-Guide",
}

# Release notes to merge into a single Release-Notes page (in display order)
RELEASE_FILES = [
    "RELEASE_NOTES.md",
    "RELEASE_NOTES_v0.5.0.md",
    "RELEASE_SUMMARY_v0.5.1.md",
    "RELEASE_v0.2.0.md",
    "RELEASE_SUCCESS_v0.2.0.md",
]


def wiki_page_name(path: str) -> str | None:
    """Return the wiki page title (without .md) for a project-relative markdown link."""
    # Check explicit aliases first
    if path in LINK_ALIASES:
        return LINK_ALIASES[path]
    if path in PAGE_MAP:
        return PAGE_MAP[path].removesuffix(".md")
    # Map skills directory to the generated index page
    if path in ("docs/skills/", "docs/skills"):
        return "Skills"
    # Try to map directory links to an index page
    if path.endswith("/"):
        key = path.rstrip("/") + "/README.md"
        if key in PAGE_MAP:
            return PAGE_MAP[key].removesuffix(".md")
    return None


def convert_link(match: re.Match, missing_links: list | None = None) -> str:
    """Convert a single markdown link target to an absolute wiki page link."""
    text = match.group(1)
    target = match.group(2)
    # Keep external links, anchors, mailto, and file URLs
    if target.startswith("http") or target.startswith("#") or target.startswith("mailto:"):
        return match.group(0)
    # Convert local file:// links to GitHub repository links
    if target.startswith("file://"):
        local_path = target.replace("file:///", "").replace("file://", "")
        # Convert Windows path to repo-relative path
        repo_rel = local_path.replace("D:/pyworkplace/ssh-mcp/", "").replace("d:/pyworkplace/ssh-mcp/", "").replace("\\", "/")
        return f"[{text}](https://github.com/Echoqili/ssh-licco/blob/master/{repo_rel})"
    # Keep image links as-is
    if match.group(0).startswith("!"):
        return match.group(0)
    # Remove anchor for page lookup
    bare = target.split("#")[0]
    page = wiki_page_name(bare)
    if page:
        anchor = "#" + target.split("#", 1)[1] if "#" in target else ""
        return f"[{text}]({WIKI_BASE_PATH}/{page}{anchor})"
    # Unknown internal markdown link: convert to plain text to avoid 404s
    if missing_links is not None and bare.endswith(".md"):
        missing_links.append((text, target))
        return text
    return match.group(0)


def convert_content(content: str, missing_links: list | None = None) -> str:
    """Convert all markdown links in content to wiki-style links."""
    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", lambda m: convert_link(m, missing_links), content)


def build_release_notes() -> str:
    """Merge all release note files into a single page."""
    parts = ["# 🚀 Release Notes\n"]
    for rel in RELEASE_FILES:
        src = PROJECT_ROOT / rel
        if not src.exists():
            print(f"Skip missing release file: {rel}")
            continue
        content = src.read_text(encoding="utf-8")
        content = convert_content(content)
        parts.append(content)
        parts.append("\n---\n")
    return "\n".join(parts)


def build_skills_index() -> str:
    """Build a skills index page from individual skill docs."""
    skills = [
        ("Skills-SSH-MCP-Setup", "💻 安装指南", "本地安装与配置"),
        ("Skills-SSH-MCP-Dev", "🛠️ 开发指南", "开发环境、流程与调试"),
        ("Skills-SSH-MCP-Ops", "⚙️ 运维指南", "运维操作最佳实践"),
        ("Skills-SSH-MCP-Troubleshoot", "🔍 故障排除", "常见问题诊断与解决"),
        ("Skills-Release", "📦 发布指南", "版本发布流程"),
        ("Skills-Git-Workflow", "🌿 Git 工作流", "Git 分支与提交规范"),
        ("Skills-OpenSpec-Workflow", "📝 OpenSpec 工作流", "规范驱动开发工作流"),
    ]
    lines = ["# 🎓 Skills 文档索引\n", "本页面汇总了 SSH LICCO 相关的 Skills 开发文档。\n"]
    for page, icon, desc in skills:
        lines.append(f"- [{icon} {desc}]({WIKI_BASE_PATH}/{page})")
    return "\n".join(lines) + "\n"


def main() -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    # Clean old markdown files but keep the .git directory
    for item in WIKI_DIR.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    missing_links: list[tuple[str, str]] = []
    for src_rel, wiki_name in PAGE_MAP.items():
        src_path = PROJECT_ROOT / src_rel
        if not src_path.exists():
            print(f"Skip missing: {src_rel}")
            continue
        content = src_path.read_text(encoding="utf-8")
        content = convert_content(content, missing_links)
        dest = WIKI_DIR / wiki_name
        dest.write_text(content, encoding="utf-8")
        print(f"Created {wiki_name}")

    if missing_links:
        print("\nUnresolved internal links converted to plain text:")
        for text, target in missing_links:
            print(f"  - '{text}' -> {target}")

    # Build merged release notes page
    release_notes = build_release_notes()
    (WIKI_DIR / "Release-Notes.md").write_text(release_notes, encoding="utf-8")
    print("Created Release-Notes.md (merged)")

    # Build skills index page
    skills_index = build_skills_index()
    (WIKI_DIR / "Skills.md").write_text(skills_index, encoding="utf-8")
    print("Created Skills.md")

    # Generate sidebar with absolute wiki paths
    sidebar = f"""# 文档导航

## 快速开始
- [🏠 首页]({WIKI_BASE_PATH}/Home)
- [📋 MCP 配置指南]({WIKI_BASE_PATH}/MCP-Config-Guide)
- [🔧 安全快速配置]({WIKI_BASE_PATH}/Security-Quick-Config)

## 参考文档
- [📊 API 参考]({WIKI_BASE_PATH}/API-Reference)
- [🔐 安全配置指南]({WIKI_BASE_PATH}/Security-Config-Guide)
- [🛡️ 安全评分总结]({WIKI_BASE_PATH}/Security-Score-Summary)
- [⚙️ 配置指南]({WIKI_BASE_PATH}/Config-Guide)

## 开发资源
- [🤝 贡献指南]({WIKI_BASE_PATH}/Contributing)
- [📖 OpenSpec 指南]({WIKI_BASE_PATH}/OpenSpec-Guide)
- [🎓 Skills 索引]({WIKI_BASE_PATH}/Skills)
- [💻 开发指南]({WIKI_BASE_PATH}/Skills-SSH-MCP-Dev)
- [🛠️ 运维指南]({WIKI_BASE_PATH}/Skills-SSH-MCP-Ops)
- [⚙️ 安装指南]({WIKI_BASE_PATH}/Skills-SSH-MCP-Setup)
- [🔍 故障排除]({WIKI_BASE_PATH}/Skills-SSH-MCP-Troubleshoot)
- [📦 发布指南]({WIKI_BASE_PATH}/Skills-Release)
- [🌿 Git 工作流]({WIKI_BASE_PATH}/Skills-Git-Workflow)
- [📝 OpenSpec 工作流]({WIKI_BASE_PATH}/Skills-OpenSpec-Workflow)

## 项目记录
- [📜 更新日志]({WIKI_BASE_PATH}/Changelog)
- [🚀 发布说明]({WIKI_BASE_PATH}/Release-Notes)
- [📓 开发日志]({WIKI_BASE_PATH}/Devlog)
- [🎓 经验教训]({WIKI_BASE_PATH}/Lessons)
"""
    (WIKI_DIR / "_Sidebar.md").write_text(sidebar, encoding="utf-8")
    print("Created _Sidebar.md")


if __name__ == "__main__":
    main()
