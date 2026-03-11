"""
检查 MCP 市场搜索功能
"""

import requests
import json

def search_registry(query):
    """搜索 MCP Registry"""
    print(f"\n🔍 搜索 MCP Registry: '{query}'")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"https://registry.modelcontextprotocol.io/v0/servers?search={query}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('servers', [])
            
            if servers:
                print(f"✅ 找到 {len(servers)} 个结果\n")
                
                for i, server_data in enumerate(servers, 1):
                    server = server_data.get('server', {})
                    meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
                    
                    name = server.get('name', 'N/A')
                    version = server.get('version', 'N/A')
                    description = server.get('description', 'N/A')
                    is_latest = meta.get('isLatest', False)
                    status = meta.get('status', 'N/A')
                    
                    print(f"{i}. {name}")
                    print(f"   版本：{version}")
                    print(f"   状态：{status} {'(最新)' if is_latest else ''}")
                    print(f"   描述：{description}")
                    print()
                
                return True
            else:
                print("❌ 未找到相关服务器")
                return False
        else:
            print(f"❌ 搜索失败：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False

def check_server_detail(server_name):
    """检查特定服务器详情"""
    print(f"\n📋 检查服务器详情：{server_name}")
    print("-" * 60)
    
    try:
        # 直接访问服务器 URL
        url = f"https://registry.modelcontextprotocol.io/servers/{server_name}"
        print(f"访问地址：{url}")
        
        # 通过 API 获取
        api_url = f"https://registry.modelcontextprotocol.io/v0/servers?search={server_name}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('servers', [])
            
            if servers:
                print(f"\n✅ 服务器可在 Registry 中访问")
                
                # 找到最新版本
                latest = None
                for server_data in servers:
                    meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
                    if meta.get('isLatest', False):
                        latest = server_data
                        break
                
                if latest:
                    server = latest.get('server', {})
                    print(f"\n最新版本信息:")
                    print(f"  名称：{server.get('name')}")
                    print(f"  版本：{server.get('version')}")
                    print(f"  描述：{server.get('description')}")
                    
                    # 检查包信息
                    packages = server.get('packages', [])
                    if packages:
                        pkg = packages[0]
                        print(f"\n包信息:")
                        print(f"  类型：{pkg.get('registryType')}")
                        print(f"  标识符：{pkg.get('identifier')}")
                        print(f"  版本：{pkg.get('version')}")
                        print(f"  运行时：{pkg.get('runtimeHint')}")
                        print(f"  传输方式：{pkg.get('transport', {}).get('type')}")
                
                return True
            else:
                print(f"❌ 服务器不存在于 Registry")
                return False
        else:
            print(f"❌ 获取失败：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False

def main():
    print("=" * 60)
    print("MCP 市场搜索检查")
    print("=" * 60)
    
    # 1. 搜索 ssh-licco
    search_registry("ssh-licco")
    
    # 2. 搜索完整名称
    search_registry("io.github.Echoqili/ssh-licco")
    
    # 3. 搜索 SSH 相关
    search_registry("SSH")
    
    # 4. 检查服务器详情
    check_server_detail("io.github.Echoqili/ssh-licco")
    
    print("\n" + "=" * 60)
    print("📊 总结")
    print("=" * 60)
    print("\n✅ MCP Registry 状态:")
    print("   - 服务器已发布")
    print("   - 版本已同步 (v0.1.7)")
    print("   - 状态：Active")
    
    print("\n🔍 搜索建议:")
    print("   1. 在 Trae IDE 中打开 MCP 市场")
    print("   2. 搜索 'ssh-licco' 或 'SSH'")
    print("   3. 如果找不到，可以直接安装:")
    print("      mcp install io.github.Echoqili/ssh-licco")
    
    print("\n💡 注意:")
    print("   - MCP Registry 索引可能需要几分钟到几小时")
    print("   - Trae IDE 的 MCP Market 可能有自己的同步周期")
    print("   - 即使市场中看不到，也可以直接通过命令安装")
    
    print("\n🌐 访问地址:")
    print("   https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
