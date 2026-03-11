"""
检查并验证 MCP Registry 发布状态
"""

import requests
import json

def check_registry_status():
    """检查 Registry 中的服务器状态"""
    print("=" * 60)
    print("MCP Registry 状态检查")
    print("=" * 60)
    
    try:
        # 查询 ssh-licco
        response = requests.get(
            "https://registry.modelcontextprotocol.io/v0/servers?search=ssh-licco",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('servers', [])
            
            if servers:
                print(f"\n✅ 找到 {len(servers)} 个版本\n")
                
                latest_version = None
                for i, server_data in enumerate(servers, 1):
                    server = server_data.get('server', {})
                    meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
                    
                    version = server.get('version', 'N/A')
                    is_latest = meta.get('isLatest', False)
                    status = meta.get('status', 'N/A')
                    published_at = meta.get('publishedAt', 'N/A')
                    
                    print(f"版本 {i}:")
                    print(f"  版本号：{version}")
                    print(f"  状态：{status}")
                    print(f"  是否最新：{is_latest}")
                    print(f"  发布时间：{published_at}")
                    
                    if is_latest:
                        latest_version = version
                    print()
                
                print("=" * 60)
                print("📊 总结")
                print("=" * 60)
                print(f"✅ 已发布到 MCP Registry")
                print(f"📦 最新版本：{latest_version}")
                print(f"🔗 查看地址：https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco")
                print(f"💡 提示：在 Trae IDE 中使用 'mcp install io.github.Echoqili/ssh-licco' 安装")
                
                return True
            else:
                print("\n❌ 未找到 ssh-licco 服务器")
                return False
        else:
            print(f"❌ 查询失败：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False

def check_pypi_status():
    """检查 PyPI 状态"""
    print("\n" + "=" * 60)
    print("PyPI 状态检查")
    print("=" * 60)
    
    try:
        response = requests.get(
            "https://pypi.org/pypi/ssh-licco/json",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            latest_version = data['info']['version']
            description = data['info']['summary']
            
            print(f"\n✅ PyPI 包信息:")
            print(f"  包名：ssh-licco")
            print(f"  最新版本：{latest_version}")
            print(f"  描述：{description}")
            print(f"  地址：https://pypi.org/project/ssh-licco/")
            
            return latest_version
        else:
            print(f"❌ 查询失败：{response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return None

def main():
    print("\n🔍 开始检查发布状态...\n")
    
    # 检查 PyPI
    pypi_version = check_pypi_status()
    
    # 检查 Registry
    registry_status = check_registry_status()
    
    # 对比版本
    print("\n" + "=" * 60)
    print("📋 版本对比")
    print("=" * 60)
    
    if pypi_version and registry_status:
        # 获取 Registry 最新版本
        response = requests.get(
            "https://registry.modelcontextprotocol.io/v0/servers?search=ssh-licco",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            registry_latest = None
            
            for server_data in data.get('servers', []):
                meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
                if meta.get('isLatest', False):
                    registry_latest = server_data.get('server', {}).get('version')
                    break
            
            print(f"\nPyPI 最新版本：{pypi_version}")
            print(f"MCP Registry 最新版本：{registry_latest}")
            
            if pypi_version != registry_latest:
                print(f"\n⚠️  版本不同步！需要发布到 MCP Registry")
                print(f"   建议：运行发布脚本更新到 v{pypi_version}")
            else:
                print(f"\n✅ 版本已同步！")
    
    print("\n" + "=" * 60)
    print("✅ 检查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
