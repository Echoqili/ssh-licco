#!/usr/bin/env python3
"""
ssh-licco CLI wrapper with smart auto-install functionality.
This is the entry point for the `ssh-licco` command.
Avoids conflicts with Anaconda/Miniconda environments.
"""
import sys
import os
import subprocess
from pathlib import Path


def diagnose_python_environment():
    """诊断当前 Python 环境"""
    current_python = sys.executable
    
    # 检测是否是 Anaconda
    is_anaconda = False
    
    # 方法1: 检查 sys.version
    version_str = sys.version.lower()
    if 'anaconda' in version_str or 'conda' in version_str or 'miniconda' in version_str:
        is_anaconda = True
    
    # 方法2: 检查环境变量
    in_conda_env = bool(os.environ.get('CONDA_PREFIX') or os.environ.get('CONDA_DEFAULT_ENV'))
    
    # 方法3: 检查可执行文件路径
    if 'anaconda' in current_python.lower() or 'miniconda' in current_python.lower():
        is_anaconda = True
    
    return {
        'is_anaconda': is_anaconda,
        'in_conda_env': in_conda_env
    }


def check_installation():
    """检查 ssh-licco 是否已安装"""
    try:
        import ssh_mcp
        return True
    except ImportError:
        return False


def auto_install(env_info):
    """自动安装 ssh-licco（如果未找到）"""
    print("🤖 ssh-licco not found, starting auto-install...", file=sys.stderr)
    
    # 如果检测到 Anaconda，给出提示
    if env_info['is_anaconda'] or env_info['in_conda_env']:
        print("⚠️ Anaconda/Miniconda detected", file=sys.stderr)
        print("   Installing in current environment to avoid conflicts...", file=sys.stderr)
    
    project_root = Path(__file__).parent.parent
    
    if (project_root / 'pyproject.toml').exists():
        print("📦 Installing from source (editable mode)...", file=sys.stderr)
        try:
            subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-e', str(project_root)
        ])
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from source: {e}", file=sys.stderr)
            return False
    else:
        print("📦 Installing from PyPI...", file=sys.stderr)
        try:
            subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 'ssh-licco'
        ])
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from PyPI: {e}", file=sys.stderr)
            return False


def main():
    # 诊断环境
    env_info = diagnose_python_environment()
    
    # 检查是否启用自动安装
    auto_install_enabled = os.environ.get('SSH_LICCO_AUTO_INSTALL', 'true').lower() != 'false'
    
    # 检查是否已安装
    if not check_installation():
        if auto_install_enabled:
            if not auto_install(env_info):
                print("❌ Auto-install failed. Please install ssh-licco manually.", file=sys.stderr)
                sys.exit(1)
            # 重新验证安装
            if not check_installation():
                print("❌ Installation verification failed.", file=sys.stderr)
                sys.exit(1)
        else:
            print("❌ ssh-licco not installed.", file=sys.stderr)
            print("Set SSH_LICCO_AUTO_INSTALL=true to enable auto-install,", file=sys.stderr)
            print("or run: pip install ssh-licco", file=sys.stderr)
            sys.exit(1)
    
    # 导入并运行实际的服务器
    from ssh_mcp.server import run_server
    run_server()


if __name__ == '__main__':
    main()
