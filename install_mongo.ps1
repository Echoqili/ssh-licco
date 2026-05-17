$password = "licco123"
$host = "192.168.58.130"
$user = "licco"

# 创建SSH命令脚本
$scriptContent = @'
#!/bin/bash

# 更新apt并安装依赖
echo "licco123" | sudo -S apt-get update
echo "licco123" | sudo -S apt-get install -y gnupg curl

# 下载MongoDB密钥
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc > /tmp/mongo-key.asc
echo "licco123" | sudo -S gpg --batch --yes -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor /tmp/mongo-key.asc

# 添加MongoDB仓库
echo "licco123" | sudo -S sh -c "echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' > /etc/apt/sources.list.d/mongodb-org-7.0.list"

# 更新apt
echo "licco123" | sudo -S apt-get update

# 安装MongoDB
echo "licco123" | sudo -S apt-get install -y mongodb-org

# 启动MongoDB服务
echo "licco123" | sudo -S systemctl start mongod
echo "licco123" | sudo -S systemctl enable mongod

# 检查状态
echo "licco123" | sudo -S systemctl status mongod
'@

$scriptContent | Out-File -FilePath "/tmp/install_mongo.sh" -Encoding utf8

# 使用plink或sshpass执行
Write-Host "Starting MongoDB installation..."
