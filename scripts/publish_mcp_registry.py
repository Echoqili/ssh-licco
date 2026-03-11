"""
自动发布到 MCP Registry 的脚本
用于 GitHub Actions 自动化
"""

import requests
import os
import json

# 配置
PYPI_PACKAGE_NAME = "ssh-licco"
SERVER_NAME = "io.github.Echoqili/ssh-licco"
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY', 'Echoqili/ssh-licco')

REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0.1"

def get_version():
    """从 pyproject.toml 获取版本号"""
    with open('pyproject.toml', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('version = '):
                version = line.split('=')[1].strip().strip('"')
                return version
    return None

def get_pypi_info(package_name, version):
    """获取 PyPI 包信息"""
    print(f"📦 获取 PyPI 包信息：{package_name} v{version}")
    
    response = requests.get(
        f"https://pypi.org/pypi/{package_name}/{version}/json",
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        return {
            "name": data['info']['name'],
            "version": data['info']['version'],
            "description": data['info']['summary'],
            "home_page": data['info'].get('home_page', ''),
        }
    else:
        print(f"❌ 获取 PyPI 信息失败：{response.status_code}")
        return None

def login_registry():
    """登录 MCP Registry"""
    print("🔐 登录 MCP Registry...")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN 未设置")
        return None
    
    response = requests.post(
        f"{REGISTRY_BASE_URL}/auth/github-at",
        json={"github_token": GITHUB_TOKEN},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print(f"✅ 登录成功！")
        return token
    else:
        print(f"❌ 登录失败：{response.status_code}")
        return None

def publish_to_registry(access_token):
    """发布到 MCP Registry"""
    version = get_version()
    if not version:
        version = "0.1.7"  # fallback
    
    print(f"🚀 发布 {SERVER_NAME} v{version} 到 MCP Registry...")
    
    # 获取 PyPI 信息
    pypi_info = get_pypi_info(PYPI_PACKAGE_NAME, version)
    if not pypi_info:
        return False
    
    # 构建发布数据
    publish_data = {
        "name": SERVER_NAME,
        "version": version,
        "description": pypi_info['description'],
        "repository": {
            "url": f"https://github.com/{GITHUB_REPOSITORY}.git",
            "source": "github"
        },
        "packages": [
            {
                "registryType": "pypi",
                "identifier": PYPI_PACKAGE_NAME,
                "version": version,
                "runtimeHint": "python",
                "transport": {
                    "type": "stdio"
                },
                "environmentVariables": [
                    {
                        "name": "SSH_HOST",
                        "description": "SSH server hostname",
                    },
                    {
                        "name": "SSH_USER",
                        "description": "SSH username",
                    },
                    {
                        "name": "SSH_PASSWORD",
                        "description": "SSH password",
                        "isSecret": True
                    },
                    {
                        "name": "SSH_PORT",
                        "description": "SSH port",
                        "default": "22"
                    }
                ]
            }
        ]
    }
    
    # 发布
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{REGISTRY_BASE_URL}/publish",
        json=publish_data,
        headers=headers,
        timeout=15
    )
    
    print(f"📊 发布响应:")
    print(f"状态码：{response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ 发布成功！")
        print(f"   查看：https://registry.modelcontextprotocol.io/servers/{SERVER_NAME}")
        return True
    else:
        print(f"❌ 发布失败：{response.status_code}")
        try:
            error_data = response.json()
            print(f"   错误：{json.dumps(error_data, indent=2)}")
        except:
            print(f"   {response.text}")
        return False

def main():
    print("=" * 60)
    print("MCP Registry 自动发布")
    print("=" * 60)
    
    # 登录
    access_token = login_registry()
    if not access_token:
        print("❌ 发布失败 - 无法登录")
        exit(1)
    
    # 发布
    success = publish_to_registry(access_token)
    
    print("=" * 60)
    if success:
        print("✅ 发布完成！")
        exit(0)
    else:
        print("❌ 发布失败")
        exit(1)

if __name__ == "__main__":
    main()
