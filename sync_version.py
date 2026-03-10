# 版本同步脚本
# 使用方法: python sync_version.py 0.1.7
import sys
import re
from pathlib import Path

def update_version(new_version: str):
    """同步更新所有版本文件"""
    
    # 1. 更新 ssh_mcp/__init__.py
    init_file = Path("ssh_mcp/__init__.py")
    content = init_file.read_text(encoding="utf-8")
    content = re.sub(
        r'^__version__ = "[\d.]+"',
        f'__version__ = "{new_version}"',
        content,
        flags=re.MULTILINE
    )
    content = re.sub(
        r'^# 版本号: [\d.]+',
        f'# 版本号: {new_version}',
        content,
        flags=re.MULTILINE
    )
    init_file.write_text(content, encoding="utf-8")
    print(f"✅ Updated ssh_mcp/__init__.py -> {new_version}")
    
    # 2. 更新 pyproject.toml
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text(encoding="utf-8")
    content = re.sub(
        r'^version = "[\d.]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )
    pyproject.write_text(content, encoding="utf-8")
    print(f"✅ Updated pyproject.toml -> {new_version}")
    
    # 3. 更新 VERSION 文件
    version_file = Path("VERSION")
    version_file.write_text(new_version, encoding="utf-8")
    print(f"✅ Updated VERSION -> {new_version}")
    
    print(f"\n🎉 Version updated to {new_version} everywhere!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_version.py <version>")
        print("Example: python sync_version.py 0.1.7")
        sys.exit(1)
    
    new_version = sys.argv[1]
    update_version(new_version)
