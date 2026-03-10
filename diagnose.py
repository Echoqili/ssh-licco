# SSH-licco 工具诊断脚本
import sys
import os
from pathlib import Path

print("=" * 60)
print("SSH-licco 工具诊断")
print("=" * 60)

# 1. 检查 Python 版本
print(f"\n[1/8] Python 版本:")
print(f"  版本：{sys.version}")
print(f"  路径：{sys.executable}")

# 2. 检查 ssh_mcp 模块
print(f"\n[2/8] ssh_mcp 模块:")
try:
    import ssh_mcp
    print(f"  ✅ 模块已导入")
    print(f"  路径：{ssh_mcp.__file__}")
    print(f"  版本：{getattr(ssh_mcp, '__version__', '未知')}")
except ImportError as e:
    print(f"  ❌ 导入失败：{e}")

# 3. 检查依赖包
print(f"\n[3/8] 依赖包检查:")
dependencies = ['mcp', 'asyncssh', 'pydantic', 'pydantic_settings']
for dep in dependencies:
    try:
        mod = __import__(dep.replace('-', '_'))
        version = getattr(mod, '__version__', '未知')
        print(f"  ✅ {dep}: {version}")
    except ImportError as e:
        print(f"  ❌ {dep}: {e}")

# 4. 检查 SSHMCPServer
print(f"\n[4/8] SSHMCPServer:")
try:
    from ssh_mcp.server import SSHMCPServer
    print(f"  ✅ 类已导入")
    server = SSHMCPServer()
    print(f"  ✅ 实例已创建")
    print(f"  服务器名称：{server.server.name}")
    print(f"  工具数量：{len(server.server._list_tools_handlers)}")
except Exception as e:
    print(f"  ❌ 错误：{e}")
    import traceback
    traceback.print_exc()

# 5. 检查 pip 安装信息
print(f"\n[5/8] pip 安装信息:")
import subprocess
result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'ssh-licco'], 
                       capture_output=True, text=True)
if result.returncode == 0:
    lines = result.stdout.strip().split('\n')
    for line in lines[:5]:  # 只显示前 5 行
        print(f"  {line}")
else:
    print(f"  ❌ 未找到安装信息")

# 6. 检查入口脚本
print(f"\n[6/8] 入口脚本:")
entry_points = [
    Path(sys.executable).parent / 'ssh-licco.exe',
    Path(sys.executable).parent / 'Scripts' / 'ssh-licco.exe',
    Path.home() / 'AppData' / 'Roaming' / 'Python' / 'Python313' / 'Scripts' / 'ssh-licco.exe',
]
for ep in entry_points:
    if ep.exists():
        print(f"  ✅ 找到：{ep}")
        print(f"     大小：{ep.stat().st_size} bytes")
    else:
        print(f"  ❌ 不存在：{ep}")

# 7. 检查环境变量
print(f"\n[7/8] SSH 环境变量:")
env_vars = ['SSH_HOST', 'SSH_USER', 'SSH_PASSWORD', 'SSH_PORT']
for var in env_vars:
    value = os.getenv(var)
    if value:
        if var == 'SSH_PASSWORD':
            print(f"  ✅ {var}: *** (已设置)")
        else:
            print(f"  ✅ {var}: {value}")
    else:
        print(f"  ⚠️  {var}: 未设置")

# 8. 检查 sys.path
print(f"\n[8/8] Python 路径:")
print(f"  路径数量：{len(sys.path)}")
site_packages_paths = [p for p in sys.path if 'site-packages' in p]
for p in site_packages_paths[:3]:
    print(f"  - {p}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

# 建议
print("\n建议:")
print("  1. 如果依赖包缺失，运行：pip install -e .")
print("  2. 如果模块导入失败，检查 Python 路径")
print("  3. 如果入口脚本不存在，重新安装：pip install -e . --user")
print("  4. 使用 Python 直接运行：python -c 'from ssh_mcp.server import run_server; run_server()'")
