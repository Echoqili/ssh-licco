# 批量删除 GitHub 仓库中的临时文件 (PowerShell 版本)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "开始清理临时文件..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 克隆仓库到临时目录
$TEMP_DIR = Join-Path $env:TEMP "ssh-licco-cleanup-$(Get-Random)"
Write-Host "`n 克隆仓库到：$TEMP_DIR" -ForegroundColor Yellow
git clone https://github.com/Echoqili/ssh-licco.git $TEMP_DIR

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 克隆失败！" -ForegroundColor Red
    exit 1
}

Set-Location $TEMP_DIR

# 配置 Git
git config user.name "GitHub Cleanup"
git config user.email "action@github.com"

# 删除文件列表
$FILES = @(
    "MARKETPLACE_SUBMISSION_COMPLETE.md",
    "MARKETPLACE_SUBMIT_GUIDE.md",
    "MARKET_SEARCH_STATUS.md",
    "MCP_MARKETPLACE_MANAGEMENT_GUIDE.md",
    "MCP_PUBLISH_GUIDE.md",
    "MCP_REGISTRY_STATUS.md",
    "MCP_SETUP_GUIDE.md",
    "PUBLISH_SUCCESS.md",
    "PUBLISH_SUMMARY.md",
    "CLEANUP_SUMMARY.md",
    "CONFIG_GUIDE.md",
    "CONFIG_MANAGEMENT_GUIDE.md",
    "CONNECTION_TEST_REPORT.md",
    "DOCKER_MCP_TIMEOUT.md",
    "DOCKER_MIRROR_SETUP.md",
    "DOCKER_OPTIMIZATION.md",
    "INSTALL_SUCCESS.md",
    "LAUNCHGUIDE.md",
    "MANAGEMENT_GUIDE_SUMMARY.md",
    "PASSWORD_SECURITY.md",
    "PROJECT_COMPLETE.md",
    "QUICK_REFERENCE_CARD.md",
    "RELEASE_GUIDE.md",
    "RELEASE_SUMMARY.md",
    "SECURITY_GUIDE.md"
)

# 删除文件
$deleted = 0
$not_found = 0

foreach ($file in $FILES) {
    if (Test-Path $file) {
        git rm $file
        Write-Host "✅ 删除：$file" -ForegroundColor Green
        $deleted++
    } else {
        Write-Host "⚠️  不存在：$file" -ForegroundColor Yellow
        $not_found++
    }
}

# 提交删除
if ($deleted -gt 0) {
    git commit -m "chore: remove $deleted temporary documentation files"
    
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "推送到 GitHub..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    git push origin master
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n============================================================" -ForegroundColor Green
        Write-Host "✅ 清理完成！" -ForegroundColor Green
        Write-Host "   - 删除：$deleted 个文件" -ForegroundColor Green
        Write-Host "   - 不存在：$not_found 个文件" -ForegroundColor Yellow
        Write-Host "============================================================" -ForegroundColor Green
    } else {
        Write-Host "`n❌ 推送失败！" -ForegroundColor Red
    }
} else {
    Write-Host "`n============================================================" -ForegroundColor Yellow
    Write-Host "⚠️  没有需要删除的文件" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
}

# 清理临时目录
Set-Location $PSScriptRoot
Remove-Item $TEMP_DIR -Recurse -Force

Write-Host "`n 临时目录已清理：$TEMP_DIR" -ForegroundColor Gray
