from ssh_mcp import SSHMCPServer
import asyncio

async def test():
    server = SSHMCPServer()
    result = await server._handle_login({'command': 'hostname && whoami && uptime'})
    print(result[0].text)
    await server.session_manager.close_all_sessions()

asyncio.run(test())
