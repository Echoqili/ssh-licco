import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.58.130', 22, 'licco', 'licco123', timeout=30)

cmds = [
    ('已安装包', 'echo licco123 | sudo -S apt list --installed 2>/dev/null | grep -i postgres'),
    ('命令检测', 'which psql 2>/dev/null; which pg_isready 2>/dev/null'),
    ('Docker', 'docker ps -a 2>/dev/null | grep -i postgres'),
    ('配置目录', 'ls /etc/postgresql/ 2>/dev/null'),
    ('库目录', 'ls /usr/lib/postgresql/ 2>/dev/null'),
    ('可安装', "apt-cache search postgresql 2>/dev/null | grep -E '^postgresql-(16|15|14)' | head -5"),
]

for title, cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout.channel.set_combine_stderr(True)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    label = out if out else '(none)'
    print('{}: {}'.format(title, label))

client.close()