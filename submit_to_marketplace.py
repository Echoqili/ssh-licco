"""
自动提交到 MCP Marketplace 的脚本
使用 GitHub API 和 MCP Registry API
"""

import requests
import json
import os
from datetime import datetime

# 配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_OWNER = 'Echoqili'
GITHUB_REPO = 'ssh-licco'
PYPI_PACKAGE = 'ssh-licco'
SERVER_NAME = 'io.github.Echoqili/ssh-licco'

def check_github_token():
    """检查 GitHub Token"""
    if not GITHUB_TOKEN:
        print("❌ 错误：未设置 GITHUB_TOKEN 环境变量")
        print("\n设置方法:")
        print("1. 访问：https://github.com/settings/tokens")
        print("2. 创建新的 Personal Access Token")
        print("3. 勾选 repo 权限")
        print("4. 复制 token 并运行:")
        print("   $env:GITHUB_TOKEN='your_token_here' (PowerShell)")
        print("   setx GITHUB_TOKEN 'your_token_here' (CMD)")
        return False
    
    print(f"✅ GitHub Token 已配置 (长度：{len(GITHUB_TOKEN)})")
    return True

def verify_github_repo():
    """验证 GitHub 仓库"""
    print(f"\n📦 验证 GitHub 仓库：{GITHUB_OWNER}/{GITHUB_REPO}")
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(
        f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}',
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 仓库存在：{data['full_name']}")
        print(f"   描述：{data.get('description', 'N/A')}")
        print(f"   默认分支：{data['default_branch']}")
        print(f"   公开：{not data['private']}")
        return True
    else:
        print(f"❌ 仓库验证失败：{response.status_code}")
        return False

def check_pypi_package():
    """检查 PyPI 包"""
    print(f"\n📦 检查 PyPI 包：{PYPI_PACKAGE}")
    
    response = requests.get(
        f'https://pypi.org/pypi/{PYPI_PACKAGE}/json',
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        latest_version = data['info']['version']
        description = data['info']['summary']
        
        print(f"✅ PyPI 包存在")
        print(f"   最新版本：{latest_version}")
        print(f"   描述：{description}")
        return True, latest_version
    else:
        print(f"❌ PyPI 包不存在：{response.status_code}")
        return False, None

def check_mcp_registry():
    """检查 MCP Registry 状态"""
    print(f"\n📋 检查 MCP Registry 状态")
    
    response = requests.get(
        f'https://registry.modelcontextprotocol.io/v0/servers?search={SERVER_NAME}',
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        servers = data.get('servers', [])
        
        if servers:
            latest = None
            for server_data in servers:
                meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
                if meta.get('isLatest', False):
                    latest = server_data
                    break
            
            if latest:
                server = latest.get('server', {})
                version = server.get('version')
                print(f"✅ 已在 MCP Registry 中")
                print(f"   服务器名称：{server.get('name')}")
                print(f"   版本：{version}")
                print(f"   描述：{server.get('description')}")
                return True
            else:
                print(f"⚠️  在 Registry 中但未找到最新版本")
                return False
        else:
            print(f"❌ 未在 MCP Registry 中找到")
            return False
    else:
        print(f"❌ 查询失败：{response.status_code}")
        return False

def create_github_release():
    """创建 GitHub Release（可选）"""
    print(f"\n 创建 GitHub Release")
    
    # 获取最新版本
    success, version = check_pypi_package()
    if not success:
        return False
    
    tag_name = f'v{version}'
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # 检查 release 是否已存在
    response = requests.get(
        f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag_name}',
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"ℹ️  Release {tag_name} 已存在，跳过创建")
        return True
    
    # 创建新的 release
    release_data = {
        'tag_name': tag_name,
        'name': tag_name,
        'body': f'''## ssh-licco v{version}

### Features
- SSH Model Context Protocol Server
- Natural language control for SSH servers
- Multiple authentication methods
- Long connection support with auto keepalive
- SFTP file transfer
- Docker support
- Background tasks

### Installation
```bash
pip install ssh-licco
# or
mcp install io.github.Echoqili/ssh-licco
```

### Links
- PyPI: https://pypi.org/project/ssh-licco/
- MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco
''',
        'draft': False,
        'prerelease': False
    }
    
    response = requests.post(
        f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases',
        headers=headers,
        json=release_data,
        timeout=15
    )
    
    if response.status_code == 201:
        print(f"✅ GitHub Release {tag_name} 创建成功")
        return True
    else:
        print(f"⚠️  创建 Release 失败：{response.status_code}")
        return True  # 不影响后续流程

def generate_marketplace_url():
    """生成 MCP Marketplace 提交 URL"""
    print(f"\n🔗 生成 MCP Marketplace 提交链接")
    
    marketplace_url = "https://github.com/marketplace/actions/mcp-server"
    
    print(f"MCP Marketplace:")
    print(f"  {marketplace_url}")
    print(f"\n直接提交链接:")
    print(f"  https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/settings/installations")
    
    return marketplace_url

def print_manual_steps():
    """打印手动提交步骤"""
    print("\n" + "=" * 60)
    print("📝 手动提交到 MCP Marketplace 的步骤")
    print("=" * 60)
    
    print("\n1️⃣ 访问 MCP Marketplace:")
    print("   https://github.com/marketplace/actions/mcp-server")
    
    print("\n2️⃣ 点击 'Create new listing' 或 'Submit your MCP server'")
    
    print("\n3️⃣ 填写信息:")
    print("   Source Code:")
    print(f"     - GitHub URL: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"     - PyPI Package: {PYPI_PACKAGE}")
    print("     - Private repository: 不勾选")
    print("     - Hide source code: 不勾选")
    
    print("\n4️⃣ 点击 'Fetch LAUNCHGUIDE.md'")
    print("   系统会自动从 GitHub 读取配置")
    
    print("\n5️⃣ 填写 Details:")
    print("   - Name: ssh-licco")
    print("   - Description: SSH Model Context Protocol Server")
    print("   - Category: Development 或 DevOps")
    print("   - Tags: ssh, mcp, ai, automation, devops")
    
    print("\n6️⃣ Pricing: 选择 Free")
    
    print("\n7️⃣ Review 并提交")
    
    print("\n" + "=" * 60)

def main():
    print("=" * 60)
    print("🚀 MCP Marketplace 自动提交工具")
    print("=" * 60)
    print(f"\n当前时间：{datetime.now()}")
    print(f"仓库：{GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"PyPI 包：{PYPI_PACKAGE}")
    print(f"MCP 服务器：{SERVER_NAME}")
    
    # 1. 检查 GitHub Token
    if not check_github_token():
        print_manual_steps()
        return
    
    # 2. 验证 GitHub 仓库
    if not verify_github_repo():
        return
    
    # 3. 检查 PyPI 包
    success, version = check_pypi_package()
    if not success:
        print("\n⚠️  PyPI 包不存在，请先发布到 PyPI")
        return
    
    # 4. 检查 MCP Registry
    in_registry = check_mcp_registry()
    
    # 5. 创建 GitHub Release（可选）
    create_github_release()
    
    # 6. 生成链接
    generate_marketplace_url()
    
    # 7. 打印手动步骤
    print_manual_steps()
    
    # 8. 总结
    print("\n" + "=" * 60)
    print("✅ 检查完成")
    print("=" * 60)
    
    if in_registry:
        print("\n🎉 你的 MCP 服务器已经发布到 MCP Registry!")
        print("   现在可以提交到 MCP Marketplace 增加曝光度")
    else:
        print("\n⚠️  建议先发布到 MCP Registry")
        print("   运行：python publish_now.py")
    
    print("\n💡 提示:")
    print("   - 已创建 LAUNCHGUIDE.md 文件")
    print("   - 在 Marketplace 页面点击 'Fetch LAUNCHGUIDE.md' 自动填充")
    print("   - 大部分信息会自动填写，只需确认即可")

if __name__ == "__main__":
    main()
