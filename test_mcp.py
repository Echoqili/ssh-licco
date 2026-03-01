#!/usr/bin/env python
"""MCP SSH 工具测试脚本"""

import os
import asyncio
import sys

sys.path.insert(0, '.')

from ssh_mcp.server import SSHMCPServer
from ssh_mcp import ConnectionConfig
from ssh_mcp.config_manager import ConfigManager
from ssh_mcp.service import get_ssh_service


def test_mcp_tools():
    """测试 MCP 工具"""
    print("=" * 50)
    print("MCP SSH 工具测试")
    print("=" * 50)

    # 1. 测试环境变量配置加载
    print("\n1. 测试环境变量配置...")
    server = SSHMCPServer()
    env_config = server._env_config
    print(f"   SSH_HOST: {env_config.get('host', 'N/A')}")
    print(f"   SSH_USER: {env_config.get('username', 'N/A')}")
    print(f"   SSH_PORT: {env_config.get('port', 'N/A')}")
    print(f"   SSH_PASSWORD: {'***已设置' if env_config.get('password') else 'N/A'}")
    print(f"   SSH_CLIENT_TYPE: {env_config.get('client_type', 'N/A')}")

    # 2. 测试配置加载
    print("\n2. 测试配置文件...")
    cm = ConfigManager()
    server_config = cm.load_server_config()
    if server_config and server_config.ssh_hosts:
        print(f"   找到 {len(server_config.ssh_hosts)} 个配置主机:")
        for host in server_config.ssh_hosts:
            print(f"   - {host.name} ({host.host}:{host.port})")
    else:
        print("   未找到配置文件中的主机")

    # 3. 测试 AsyncSSH 连接
    print("\n3. 测试 AsyncSSH 直接连接...")

    # 使用环境变量中的配置
    config = ConnectionConfig(
        host=env_config.get("host", "127.0.0.1"),
        port=int(env_config.get("port", 22)),
        username=env_config.get("username", "root"),
        password=env_config.get("password", ""),
        client_type=env_config.get("client_type", "asyncssh")
    )

    print(f"   主机: {config.host}")
    print(f"   端口: {config.port}")
    print(f"   用户: {config.username}")
    print(f"   客户端: {config.client_type}")

    if not config.password:
        print("   错误: 密码为空!")
        return

    try:
        service = get_ssh_service()

        print("   正在连接...")
        session_info = service.connect(config)
        print(f"   连接成功! Session ID: {session_info.session_id}")

        print("   执行命令: uptime && whoami")
        result = service.execute_command(session_info.session_id, "uptime && whoami")
        print(f"   输出:\n{result['stdout']}")

        print("   正在断开...")
        service.disconnect(session_info.session_id)
        print("   断开成功!")

    except Exception as e:
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    test_mcp_tools()
