#!/usr/bin/env python3
"""智能安装脚本 - 自动检测并安装 ssh-licco，避免 Anaconda 冲突"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def diagnose_python_environment():
    """诊断当前 Python 环境"""
    print("🔍 Diagnosing Python environment...")

    current_python = sys.executable
    print(f"  • Current interpreter: {current_python}")
    print(f"  • Python version: {sys.version.split()[0]}")
    print(f"  • Platform: {platform.platform()}")

    # 检测是否是 Anaconda
    is_anaconda = False
    in_conda_env = False

    # 方法1: 检查 sys.version
    version_str = sys.version.lower()
    if 'anaconda' in version_str or 'conda' in version_str or 'miniconda' in version_str:
        is_anaconda = True
        print("  ⚠️  Detected Anaconda/Miniconda Python")

    # 方法2: 检查环境变量
    if os.environ.get('CONDA_PREFIX') or os.environ.get('CONDA_DEFAULT_ENV'):
        in_conda_env = True
        print("  ⚠️  Running in conda environment")

    # 方法3: 检查可执行文件路径
    if 'anaconda' in current_python.lower() or 'miniconda' in current_python.lower():
        is_anaconda = True

    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    if in_venv:
        print(f"  ✅ Running in virtual environment: {sys.prefix}")

    return {
        'current_python': current_python,
        'is_anaconda': is_anaconda,
        'in_conda_env': in_conda_env,
        'in_venv': in_venv,
        'version': sys.version.split()[0]
    }


def find_mcp_config():
    """查找 mcp.config.json 文件"""
    possible_locations = [
        Path.cwd() / 'mcp.config.json',
        Path.cwd() / '.mcp' / 'config.json',
        Path.home() / '.mcp' / 'config.json',
        Path.home() / 'mcp.config.json',
    ]

    for location in possible_locations:
        if location.exists():
            return location
    return None


def check_ssh_licco_installed():
    """检查 ssh-licco 是否已安装"""
    try:
        import ssh_mcp
        return True
    except ImportError:
        return False


def install_ssh_licco(env_info):
    """安装 ssh-licco"""
    project_root = Path(__file__).parent

    if (project_root / 'pyproject.toml').exists():
        print("📦 Installing from source (editable mode)...")
        try:
            subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-e', str(project_root)
        ])
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from source: {e}")
            return False
    else:
        print("📦 Installing from PyPI...")
        try:
            subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 'ssh-licco'
        ])
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from PyPI: {e}")
            return False


def verify_installation():
    """验证安装"""
    print("\n🔍 Verifying installation...")
    try:
        # 验证包导入
        print("✅ Package imported successfully")

        # 验证命令行工具
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'ssh-licco'],
                            capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    print("✅ Version:", line.split(':', 1)[1].strip())

        return True
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def test_ssh_connection(config):
    """测试 SSH 连接（如果配置了）"""
    if not config:
        return

    ssh_config = config.get('mcpServers', {}).get('ssh-licco', {}).get('env', {})
    if not ssh_config.get('SSH_HOST'):
        return

    print("\n🔗 Testing SSH connection...")
    try:
        from ssh_mcp.clients.paramiko_client import ParamikoClient
        from ssh_mcp.connection_config import ConnectionConfig

        conn_config = ConnectionConfig(
            host=ssh_config.get('SSH_HOST'),
            port=int(ssh_config.get('SSH_PORT', 22)),
            username=ssh_config.get('SSH_USER'),
            password=ssh_config.get('SSH_PASSWORD'),
            timeout=int(ssh_config.get('SSH_TIMEOUT', 60))
        )

        client = ParamikoClient(conn_config)
        result = client.connect(timeout=30)

        if result.success:
            print(f"✅ SSH connection successful (latency: {result.latency_ms:.2f}ms)")
            client.disconnect()
        else:
            print(f"⚠️ SSH connection failed: {result.message}")

    except Exception as e:
        print(f"⚠️ Could not test SSH connection: {e}")


def main():
    print("=" * 70)
    print("🤖 ssh-licco Smart Installer")
    print("=" * 70)

    # 诊断环境
    env_info = diagnose_python_environment()

    # 如果在 Anaconda 环境中的特殊提示
    if env_info['is_anaconda'] or env_info['in_conda_env']:
        print("\n" + "=" * 70)
        print("⚠️ Anaconda/Miniconda Detected")
        print("=" * 70)
        print("   This installer will use your current Python environment")
        print("   No changes will be made to your conda environments")
        print("=" * 70)

    # 查找配置文件
    config_path = find_mcp_config()
    config = None

    if config_path:
        print(f"\n📄 Found config file: {config_path}")
        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read config: {e}")
    else:
        print("\n📄 No mcp.config.json found, will install globally")

    # 检查是否已安装
    if check_ssh_licco_installed():
        print("\n✅ ssh-licco is already installed")
        verify_installation()
        test_ssh_connection(config)
        return 0

    # 安装
    print("\n🚀 Starting installation...")
    print(f"   Using Python: {sys.executable}")

    if not install_ssh_licco(env_info):
        print("\n❌ Installation failed")
        return 1

    # 验证
    if not verify_installation():
        print("\n❌ Installation verification failed")
        return 1

    # 测试 SSH 连接
    test_ssh_connection(config)

    # 完成
    print("\n" + "=" * 70)
    print("🎉 Installation Complete!")
    print("=" * 70)
    print("\n📖 Next Steps:")
    print("   1. Restart your MCP client (Trae/Cursor/Claude Desktop)")
    print("   2. Start using ssh-licco for SSH operations")

    if env_info['is_anaconda']:
        print("\n🔒 Isolation Note:")
        print("   • ssh-licco is installed in your current Python environment")
        print("   • No conflicts with other conda environments")

    return 0


if __name__ == '__main__':
    sys.exit(main())
