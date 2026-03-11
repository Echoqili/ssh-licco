"""
直接发布到 MCP Registry 的脚本 - 修复版
"""

import requests
import json
import os

# 配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
PYPI_PACKAGE_NAME = "ssh-licco"
SERVER_NAME = "io.github.Echoqili/ssh-licco"
VERSION = "0.1.7"

REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0.1"

def main():
    print("=" * 60)
    print("🚀 MCP Registry 直接发布")
    print("=" * 60)
    
    if not GITHUB_TOKEN:
        print("❌ 错误：未设置 GITHUB_TOKEN 环境变量")
        print(f"   Token 前缀：{GITHUB_TOKEN[:10] if GITHUB_TOKEN else 'None'}...")
        return
    
    print(f"📝 Token 长度：{len(GITHUB_TOKEN)}")
    print(f"📝 Token 前缀：{GITHUB_TOKEN[:10]}...")
    
    # 1. 登录
    print("\n🔐 登录 MCP Registry...")
    try:
        response = requests.post(
            f"{REGISTRY_BASE_URL}/auth/github-at",
            json={"github_token": GITHUB_TOKEN},
            timeout=10
        )
        
        print(f"   响应状态：{response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 登录失败：{response.status_code}")
            print(f"   {response.text[:200]}")
            return
        
        auth_data = response.json()
        access_token = auth_data.get('registry_token') or auth_data.get('access_token')
        
        if not access_token:
            print(f"❌ 未获取到 registry_token")
            print(f"   响应：{json.dumps(auth_data, indent=2)}")
            return
        
        print(f"✅ 登录成功！")
        print(f"   Token 前缀：{access_token[:20]}...")
        
    except Exception as e:
        print(f"❌ 登录错误：{e}")
        return
    
    # 2. 获取 PyPI 信息
    print(f"\n📦 获取 PyPI 信息：{PYPI_PACKAGE_NAME} v{VERSION}")
    try:
        response = requests.get(
            f"https://pypi.org/pypi/{PYPI_PACKAGE_NAME}/{VERSION}/json",
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ 获取 PyPI 信息失败：{response.status_code}")
            return
        
        pypi_data = response.json()
        description = pypi_data['info']['summary']
        print(f"✅ 描述：{description}")
        
    except Exception as e:
        print(f"❌ PyPI 错误：{e}")
        return
    
    # 3. 构建发布数据
    print(f"\n🚀 准备发布 {SERVER_NAME} v{VERSION}...")
    
    publish_data = {
        "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
        "name": SERVER_NAME,
        "version": VERSION,
        "description": description,
        "repository": {
            "url": "https://github.com/Echoqili/ssh-licco.git",
            "source": "github"
        },
        "packages": [
            {
                "registryType": "pypi",
                "identifier": PYPI_PACKAGE_NAME,
                "version": VERSION,
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
    
    # 4. 发布
    print("\n📤 提交到 MCP Registry...")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{REGISTRY_BASE_URL}/publish",
            json=publish_data,
            headers=headers,
            timeout=15
        )
        
        print(f"\n📊 响应状态：{response.status_code}")
        
        if response.status_code == 200:
            print(f"\n✅✅✅ 发布成功！✅✅✅")
            print(f"\n📍 查看地址:")
            print(f"   https://registry.modelcontextprotocol.io/servers/{SERVER_NAME}")
            print(f"\n💡 在 Trae IDE 中使用:")
            print(f"   mcp install {SERVER_NAME}")
        else:
            print(f"\n❌ 发布失败：{response.status_code}")
            try:
                error_data = response.json()
                print(f"   错误信息：{json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   {response.text[:500]}")
    
    except Exception as e:
        print(f"\n❌ 发布错误：{e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
