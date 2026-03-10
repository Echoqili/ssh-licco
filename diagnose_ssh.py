# SSH 连接诊断脚本
import json
import os
import paramiko
import time

print("=" * 60)
print("SSH 连接诊断")
print("=" * 60)

# 1. 测试密码读取
print("\n[1] 测试密码解析")
password = "P/[KY}+wa7?2|uc"
print(f"   硬编码密码：{password}")
print(f"   长度：{len(password)}")

# 2. 测试环境变量
print("\n[2] 测试环境变量")
os.environ['SSH_PASSWORD'] = password
os.environ['SSH_HOST'] = '43.143.207.242'
os.environ['SSH_USER'] = 'root'
os.environ['SSH_PORT'] = '22'

env_password = os.getenv('SSH_PASSWORD')
print(f"   环境变量密码：{env_password}")
print(f"   匹配：{env_password == password}")

# 3. 测试网络连接
print("\n[3] 测试网络连接")
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex(('43.143.207.242', 22))
    if result == 0:
        print(f"   ✅ 端口 22 开放")
    else:
        print(f"   ❌ 端口 22 无法连接 (错误码：{result})")
    sock.close()
except Exception as e:
    print(f"   ❌ 网络测试失败：{e}")

# 4. 测试 SSH Banner
print("\n[4] 测试 SSH Banner")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect(('43.143.207.242', 22))
    banner = sock.recv(1024).decode('utf-8')
    print(f"   ✅ SSH Banner: {banner.strip()}")
    sock.close()
except socket.timeout:
    print(f"   ❌ 读取 Banner 超时")
    print(f"   💡 这是 SSH 服务器问题，不是密码问题")
except Exception as e:
    print(f"   ❌ SSH 协议测试失败：{e}")

# 5. 尝试 SSH 连接
print("\n[5] 尝试 SSH 连接")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"   正在连接...")
    client.connect(
        hostname='43.143.207.242',
        port=22,
        username='root',
        password=password,
        timeout=120,
        banner_timeout=120,
        auth_timeout=120
    )
    print(f"   ✅ 连接成功！")
    client.close()
except paramiko.AuthenticationException as e:
    print(f"   ❌ 认证失败：{e}")
    print(f"   💡 密码错误")
except paramiko.SSHException as e:
    if "Error reading SSH protocol banner" in str(e):
        print(f"   ❌ SSH Banner 读取失败")
        print(f"   💡 SSH 服务器无响应，需要重启服务器 SSH 服务")
    else:
        print(f"   ❌ SSH 错误：{e}")
except Exception as e:
    print(f"   ❌ 连接失败：{e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
