# SSH LICCO Docker 构建脚本 (Windows PowerShell)
# 自动检测网络环境并选择最优镜像源

Write-Host "🚀 开始构建 SSH LICCO Docker 镜像..." -ForegroundColor Green

# Docker 镜像加速器列表
$DOCKER_MIRRORS = @(
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

# 检测是否在中国大陆
Write-Host "`n📡 检测网络环境..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://pypi.tuna.tsinghua.edu.cn" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ 使用清华大学镜像源（中国大陆）" -ForegroundColor Green
    $PIP_ARG = "--build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
} catch {
    Write-Host "✅ 使用官方 PyPI 源" -ForegroundColor Green
    $PIP_ARG = ""
}

# 构建 Docker 镜像加速器 JSON 数组
$MIRRORS_JSON = ($DOCKER_MIRRORS | ForEach-Object { "`"$_`"" }) -join ","
$MIRROR_ARG = "--build-arg DOCKER_MIRRORS='[$MIRRORS_JSON]'"

# 构建镜像
Write-Host "`n🔨 构建 Docker 镜像..." -ForegroundColor Cyan
Write-Host "📦 使用 Docker 镜像加速器..." -ForegroundColor Cyan
docker build $PIP_ARG $MIRROR_ARG `
    -t ssh-licco:latest `
    -t ssh-licco:0.1.6 `
    --progress=plain `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 构建完成！" -ForegroundColor Green
    Write-Host "`n📦 镜像信息:" -ForegroundColor Yellow
    docker images ssh-licco
    
    Write-Host "`n💡 使用提示:" -ForegroundColor Yellow
    Write-Host "   运行测试：docker run --rm ssh-licco:latest --help"
    Write-Host "   查看镜像：docker images ssh-licco"
    Write-Host "   推送镜像：docker push ssh-licco:latest"
} else {
    Write-Host "`n❌ 构建失败！" -ForegroundColor Red
    exit 1
}
