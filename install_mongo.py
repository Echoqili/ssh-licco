import paramiko
import time

def execute_ssh_command(host, username, password, command, sudo=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=username, password=password, timeout=30)
        
        if sudo:
            command = f"echo '{password}' | sudo -S {command}"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        return {
            'exit_code': exit_status,
            'stdout': output,
            'stderr': error
        }
    finally:
        ssh.close()

def install_mongodb():
    host = "192.168.58.130"
    username = "licco"
    password = "licco123"
    
    print("🚀 Starting MongoDB installation...")
    
    print("\n1. Updating apt-get...")
    result = execute_ssh_command(host, username, password, "apt-get update", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"stderr: {result['stderr'][:500]}")
    
    print("\n2. Installing gnupg and curl...")
    result = execute_ssh_command(host, username, password, "apt-get install -y gnupg curl", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stdout']:
        print(f"stdout: {result['stdout'][:500]}")
    if result['stderr']:
        print(f"stderr: {result['stderr'][:500]}")
    
    print("\n3. Downloading MongoDB GPG key...")
    result = execute_ssh_command(host, username, password, "curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc > /tmp/mongo-key.asc")
    print(f"Exit code: {result['exit_code']}")
    
    print("\n4. Adding GPG key...")
    result = execute_ssh_command(host, username, password, "gpg --batch --yes -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor /tmp/mongo-key.asc", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"stderr: {result['stderr'][:500]}")
    
    print("\n5. Adding MongoDB repository...")
    result = execute_ssh_command(host, username, password, "sh -c \"echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' > /etc/apt/sources.list.d/mongodb-org-7.0.list\"", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    
    print("\n6. Updating apt-get again...")
    result = execute_ssh_command(host, username, password, "apt-get update", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"stderr: {result['stderr'][:500]}")
    
    print("\n7. Installing MongoDB...")
    result = execute_ssh_command(host, username, password, "apt-get install -y mongodb-org", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stdout']:
        print(f"stdout: {result['stdout'][:500]}")
    if result['stderr']:
        print(f"stderr: {result['stderr'][:500]}")
    
    print("\n8. Starting MongoDB service...")
    result = execute_ssh_command(host, username, password, "systemctl start mongod", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    
    print("\n9. Enabling MongoDB on boot...")
    result = execute_ssh_command(host, username, password, "systemctl enable mongod", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    
    print("\n10. Checking MongoDB status...")
    result = execute_ssh_command(host, username, password, "systemctl status mongod", sudo=True)
    print(f"Exit code: {result['exit_code']}")
    if result['stdout']:
        print(f"stdout:\n{result['stdout']}")
    if result['stderr']:
        print(f