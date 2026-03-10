#!/usr/bin/env pwsh
# Docker 镜像加速器配置脚本
# 自动配置 Docker Daemon 使用中国大陆镜像加速器

$ErrorActionPreference = "Stop"

Write-Host "🔧 Docker 镜像加速器配置工具" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Docker 镜像加速器列表
$MIRRORS = @(
    "https://docker.registry.cyou",
    "https://docker-cf.registry.cyou",
    "https://dockercf.jsdelivr.fyi",
    "https://docker.jsdelivr.fyi",
    "https://dockertest.jsdelivr.fyi",
    "https://mirror.aliyuncs.com",
    "https://dockerproxy.com",
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.iscas.ac.cn",
    "https://docker.rainbond.cc"
)

# Docker 配置目录
$DOCKER_CONFIG_DIR = "C:\ProgramData\docker\config"
$DOCKER_CONFIG_FILE = "$DOCKER_CONFIG_DIR\daemon.json"

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 错误：请以管理员身份运行此脚本" -ForegroundColor Red
    Write-Host "   右键点击 PowerShell -> 以管理员身份运行" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✅ 管理员权限已确认" -ForegroundColor Green

# 检查 Docker 是否安装
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker 已安装：$dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误：Docker 未安装" -ForegroundColor Red
    exit 1
}

# 创建配置目录
if (-not (Test-Path $DOCKER_CONFIG_DIR)) {
    Write-Host "`n📁 创建配置目录：$DOCKER_CONFIG_DIR" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $DOCKER_CONFIG_DIR -Force | Out-Null
    Write-Host "✅ 目录创建成功" -ForegroundColor Green
} else {
    Write-Host "`n✅ 配置目录已存在" -ForegroundColor Green
}

# 备份现有配置
if (Test-Path $DOCKER_CONFIG_FILE) {
    Write-Host "`n💾 备份现有配置..." -ForegroundColor Yellow
    $backupFile = "$DOCKER_CONFIG_FILE.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $DOCKER_CONFIG_FILE $backupFile
    Write-Host "✅ 备份到：$backupFile" -ForegroundColor Green
}

# 创建新的 daemon.json 配置
Write-Host "`n⚙️  创建 Docker 配置..." -ForegroundColor Yellow

$config = @{
    "registry-mirrors" = $MIRRORS
    "insecure-registries" = @()
    "max-concurrent-downloads" = 10
    "max-concurrent-uploads" = 5
    "log-opts" = @{
        "max-size" = "100m"
        "max-file" = 3
    }
}

# 保存配置
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $DOCKER_CONFIG_FILE -Encoding UTF8
    Write-Host "✅ 配置文件已保存：$DOCKER_CONFIG_FILE" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误：无法保存配置文件" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# 重启 Docker 服务
Write-Host "`n🔄 重启 Docker 服务..." -ForegroundColor Yellow
try {
    Restart-Service -Name "docker" -Force
    Write-Host "✅ Docker 服务已重启" -ForegroundColor Green
} catch {
    Write-Host "⚠️  警告：无法自动重启 Docker 服务" -ForegroundColor Yellow
    Write-Host "   请手动重启 Docker Desktop 或运行：Restart-Service docker" -ForegroundColor Yellow
}

# 验证配置
Write-Host "`n🔍 验证配置..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $info = docker info
    if ($info -match "Registry Mirrors") {
        Write-Host "✅ Docker 镜像加速器配置成功！" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  请手动检查 Docker 配置" -ForegroundColor Yellow
}

Write-Host "`n📋 配置摘要:" -ForegroundColor Cyan
Write-Host "配置文件：$DOCKER_CONFIG_FILE" -ForegroundColor White
Write-Host "镜像加速器数量：$($MIRRORS.Count)" -ForegroundColor White
Write-Host ""
Write-Host "🎉 配置完成！" -ForegroundColor Green
Write-Host ""
Write-Host "💡 提示：" -ForegroundColor Yellow
Write-Host "  - 查看配置：cat $DOCKER_CONFIG_FILE" -ForegroundColor White
Write-Host "  - 测试构建：docker build -t ssh-licco:latest ." -ForegroundColor White
Write-Host "  - 查看镜像信息：docker info | Select-String 'Registry Mirrors'" -ForegroundColor White
