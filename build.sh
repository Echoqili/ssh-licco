#!/bin/bash

# SSH LICCO Docker 构建脚本
# 自动检测网络环境并选择最优镜像源

set -e

echo "🚀 开始构建 SSH LICCO Docker 镜像..."

# 检测是否在中国大陆
echo "📡 检测网络环境..."
if curl -s --connect-timeout 3 https://pypi.tuna.tsinghua.edu.cn > /dev/null 2>&1; then
    echo "✅ 使用清华大学镜像源（中国大陆）"
    BUILD_ARG="--build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
else
    echo "✅ 使用官方 PyPI 源"
    BUILD_ARG=""
fi

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker build $BUILD_ARG \
    -t ssh-licco:latest \
    -t ssh-licco:0.1.6 \
    --progress=plain \
    .

echo "✅ 构建完成！"
echo ""
echo "📦 镜像信息:"
docker images ssh-licco

echo ""
echo "💡 使用提示:"
echo "   运行测试：docker run --rm ssh-licco:latest --help"
echo "   查看镜像：docker images ssh-licco"
echo "   推送镜像：docker push ssh-licco:latest"
