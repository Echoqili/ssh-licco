# SSH LICCO - Optimized Dockerfile
# 优化构建速度的关键策略：
# 1. 使用多阶段构建减少最终镜像大小
# 2. 分离依赖安装和代码复制以利用 Docker 缓存
# 3. 使用国内镜像源加速下载（可选）
# 4. 精简基础镜像
# 5. 支持多种 Docker 镜像加速器

# 构建参数：Docker 镜像加速器列表
# 使用方法：docker build --build-arg DOCKER_MIRRORS='["https://mirror.aliyuncs.com","https://dockerproxy.com"]' .
ARG DOCKER_MIRRORS='["https://docker.registry.cyou","https://docker-cf.registry.cyou","https://dockercf.jsdelivr.fyi","https://docker.jsdelivr.fyi","https://dockertest.jsdelivr.fyi","https://mirror.aliyuncs.com","https://dockerproxy.com","https://mirror.baidubce.com","https://docker.m.daocloud.io","https://docker.nju.edu.cn","https://docker.mirrors.sjtug.sjtu.edu.cn","https://docker.mirrors.ustc.edu.cn","https://mirror.iscas.ac.cn","https://docker.rainbond.cc"]'

# ==================== 构建阶段 ====================
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 先复制依赖文件（利用 Docker 缓存）
# 这样可以缓存 pip install 的结果
COPY pyproject.toml ./

# 安装依赖（使用国内镜像源加速）
# 如果在国内，取消下面一行的注释
# RUN pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple .
RUN pip install --no-cache-dir .

# ==================== 运行阶段 ====================
FROM python:3.11-slim as runtime

# 设置工作目录
WORKDIR /app

# 安装运行时依赖（仅 SSH 客户端）
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY ssh_mcp/ ./ssh_mcp/

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

# 设置入口点
ENTRYPOINT ["ssh-licco"]

# 默认不传参数，等待 MCP 客户端调用
CMD []
