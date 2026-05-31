"""
自动发布到 MCP Registry 的脚本
用于 GitHub Actions 自动化

参考官方文档:
  https://modelcontextprotocol.io/tools/registry/publishing/
  https://raw.githubusercontent.com/modelcontextprotocol/registry/refs/heads/main/docs/reference/server-json/generic-server-json.md
"""

import requests
import os
import json
import time

# 配置
PYPI_PACKAGE_NAME = "ssh-licco"
SERVER_NAME = "io.github.Echoqili/ssh-licco"
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY', 'Echoqili/ssh-licco')

REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0.1"
SCHEMA_URL = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"

def get_version():
    """从 pyproject.toml 获取版本号"""
    with open('pyproject.toml', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('version = '):
                version = line.split('=')[1].strip().strip('"')
                return version
    return None

def login_registry():
    """登录 MCP Registry"""
    print("[DEBUG] 开始登录 MCP Registry...")
    
    if not GITHUB_TOKEN:
        print("[ERROR] GITHUB_TOKEN 环境变量为空！")
        return None
    
    print(f"[DEBUG] GITHUB_TOKEN 长度: {len(GITHUB_TOKEN)}")
    
    try:
        response = requests.post(
            f"{REGISTRY_BASE_URL}/auth/github-at",
            json={"github_token": GITHUB_TOKEN},
            timeout=30
        )
        
        print(f"[DEBUG] 登录 API 响应: status={response.status_code}")
        print(f"[DEBUG] 登录 API 响应体: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('registry_token') or data.get('access_token')
            print(f"[DEBUG] 解析到 registry_token: {'有值' if token else 'None'}")
            if token:
                print(f"[DEBUG] token 长度: {len(token)}")
                print("[OK] 登录成功！")
                return token
            else:
                print("[ERROR] 登录响应 200 但没有有效 token！完整响应:")
                print(json.dumps(data, indent=2))
                return None
        else:
            print(f"[ERROR] 登录 API 返回非 200: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[ERROR] 登录请求异常: {e}")
        return None

def build_publish_data(version):
    """
    按照 MCP Registry 官方规范构建发布数据
    
    参考: https://raw.githubusercontent.com/modelcontextprotocol/registry/refs/heads/main/docs/reference/server-json/generic-server-json.md
    """
    publish_data = {
        "$schema": SCHEMA_URL,
        "name": SERVER_NAME,
        "description": "SSH Model Context Protocol Server - Enable SSH functionality for AI models",
        "title": "SSH LICCO MCP Server",
        "version": version,
        "repository": {
            "url": f"https://github.com/{GITHUB_REPOSITORY}.git",
            "source": "github"
        },
        "packages": [
            {
                "registryType": "pypi",
                "registryBaseUrl": "https://pypi.org",
                "identifier": PYPI_PACKAGE_NAME,
                "version": version,
                "runtimeHint": "python",
                "transport": {
                    "type": "stdio"
                },
                "environmentVariables": [
                    {
                        "name": "SSH_HOST",
                        "description": "SSH server hostname or IP address",
                        "isRequired": True,
                    },
                    {
                        "name": "SSH_USER",
                        "description": "SSH username for authentication",
                        "isRequired": True,
                    },
                    {
                        "name": "SSH_PASSWORD",
                        "description": "SSH password for authentication",
                        "isRequired": False,
                        "isSecret": True
                    },
                    {
                        "name": "SSH_PORT",
                        "description": "SSH port number",
                        "isRequired": False,
                        "default": "22"
                    }
                ]
            }
        ],
    }
    
    return publish_data

def publish_to_registry(access_token):
    """发布到 MCP Registry"""
    version = get_version()
    if not version:
        version = "1.1.7"
    
    print(f"[DEBUG] 准备发布 {SERVER_NAME} v{version}")
    
    publish_data = build_publish_data(version)
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"[DEBUG] 发送发布请求到 {REGISTRY_BASE_URL}/publish")
    print(f"[DEBUG] $schema: {publish_data['$schema']}")
    print(f"[DEBUG] 请求数据大小: {len(json.dumps(publish_data))} bytes")
    
    try:
        response = requests.post(
            f"{REGISTRY_BASE_URL}/publish",
            json=publish_data,
            headers=headers,
            timeout=120
        )
        
        print(f"[DEBUG] 发布 API 响应: status={response.status_code}")
        print(f"[DEBUG] 发布 API 响应体: {response.text[:1000]}")
        
        if response.status_code == 200:
            print(f"[OK] 发布成功！")
            print(f"     查看：https://registry.modelcontextprotocol.io/servers/{SERVER_NAME}")
            return True
        else:
            print(f"[ERROR] 发布失败: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"[ERROR] 错误详情: {json.dumps(error_data, indent=2)}")
            except:
                print(f"[ERROR] 响应文本: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 发布请求异常: {e}")
        return False

def main():
    print("=" * 60)
    print("MCP Registry 自动发布")
    print("=" * 60)
    
    access_token = login_registry()
    if not access_token:
        print("=" * 60)
        print("[FAIL] 发布终止 - 登录失败或无有效 token")
        exit(1)
    
    success = publish_to_registry(access_token)
    
    print("=" * 60)
    if success:
        print("[SUCCESS] 全部完成！")
        exit(0)
    else:
        print("[FAIL] 发布失败")
        exit(1)

if __name__ == "__main__":
    main()
