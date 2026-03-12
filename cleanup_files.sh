#!/bin/bash
# 批量删除 GitHub 仓库中的临时文件

echo "============================================================"
echo "开始清理临时文件..."
echo "============================================================"

# 克隆仓库到临时目录
TEMP_DIR="/tmp/ssh-licco-cleanup-$$"
echo "克隆仓库到：$TEMP_DIR"
git clone https://github.com/Echoqili/ssh-licco.git "$TEMP_DIR"
cd "$TEMP_DIR"

# 配置 Git
git config user.name "GitHub Cleanup"
git config user.email "action@github.com"

# 删除文件列表
FILES=(
"MARKETPLACE_SUBMISSION_COMPLETE.md"
"MARKETPLACE_SUBMIT_GUIDE.md"
"MARKET_SEARCH_STATUS.md"
"MCP_MARKETPLACE_MANAGEMENT_GUIDE.md"
"MCP_PUBLISH_GUIDE.md"
"MCP_REGISTRY_STATUS.md"
"MCP_SETUP_GUIDE.md"
"PUBLISH_SUCCESS.md"
"PUBLISH_SUMMARY.md"
"CLEANUP_SUMMARY.md"
"CONFIG_GUIDE.md"
"CONFIG_MANAGEMENT_GUIDE.md"
"CONNECTION_TEST_REPORT.md"
"DOCKER_MCP_TIMEOUT.md"
"DOCKER_MIRROR_SETUP.md"
"DOCKER_OPTIMIZATION.md"
"INSTALL_SUCCESS.md"
"LAUNCHGUIDE.md"
"MANAGEMENT_GUIDE_SUMMARY.md"
"PASSWORD_SECURITY.md"
"PROJECT_COMPLETE.md"
"QUICK_REFERENCE_CARD.md"
"RELEASE_GUIDE.md"
"RELEASE_SUMMARY.md"
"SECURITY_GUIDE.md"
)

# 删除文件
deleted=0
not_found=0

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        git rm "$file"
        echo "✅ 删除：$file"
        ((deleted++))
    else
        echo "⚠️  不存在：$file"
        ((not_found++))
    fi
done

# 提交删除
if [ $deleted -gt 0 ]; then
    git commit -m "chore: remove $deleted temporary documentation files"
    
    echo ""
    echo "============================================================"
    echo "推送到 GitHub..."
    echo "============================================================"
    git push origin master
    
    echo ""
    echo "============================================================"
    echo "✅ 清理完成！"
    echo "   - 删除：$deleted 个文件"
    echo "   - 不存在：$not_found 个文件"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "⚠️  没有需要删除的文件"
    echo "============================================================"
fi

# 清理临时目录
cd ..
rm -rf "$TEMP_DIR"
