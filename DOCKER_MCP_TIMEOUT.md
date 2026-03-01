# Docker 构建时 MCP 超时问题说明

## 问题原因

当你在 Dockerfile 中执行 `RUN ssh-licco` 或类似命令时，构建会超时，原因如下：

### 1. **MCP 服务器的工作原理**
```python
async def run(self):
    async with stdio_server() as (read_stream, write_stream):
        await self.server.run(
            read_stream,
            write_stream,
            self.server.create_initialization_options()
        )
```

MCP 服务器使用 **stdio 传输协议**，需要：
- ✅ 持续的标准输入/输出连接
- ✅ 与 MCP 客户端（AI 助手）的双向通信
- ✅ 等待客户端发送工具和命令请求
- ✅ 保持后台运行以维持 SSH 会话

### 2. **Docker 构建环境的限制**

| 特性 | MCP 服务器需求 | Docker 构建环境 |
|------|---------------|----------------|
| 输入流 | 需要持续等待输入 | 单向执行，无交互 |
| 运行时间 | 持久运行 | 每个 RUN 步骤独立且短暂 |
| 通信 | 双向 stdio 通信 | 仅输出日志 |
| 进程模型 | 后台服务 | 前台命令执行 |

### 3. **超时流程**
```
Docker 构建开始
    ↓
执行 RUN ssh-licco
    ↓
MCP 服务器启动
    ↓
等待客户端连接 (stdio)
    ↓
等待...等待...等待...
    ↓
⏰ Docker 构建超时 (默认无输出超时)
    ↓
构建失败 ❌
```

## 解决方案

### ❌ 错误用法

```dockerfile
# 不要这样做！
FROM python:3.11

RUN pip install ssh-licco
RUN ssh-licco  # ❌ 会超时！
```

### ✅ 正确用法

#### 方案 1：在宿主机运行 MCP 服务器

**步骤：**

1. **在宿主机安装 ssh-licco**
```bash
pip install ssh-licco
```

2. **配置 MCP 客户端**
在 Trae/Cursor/Claude Desktop 的配置文件中：
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

3. **使用 AI 助手操作 Docker**
直接告诉 AI：
```
帮我构建 Docker 镜像
```

AI 会通过 MCP 执行：
```bash
docker build -t myapp .
```

#### 方案 2：在 Docker 容器内安装 SSH 客户端

如果你需要在容器内使用 SSH：

```dockerfile
FROM python:3.11-slim

# 安装 SSH 客户端
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# 正常运行你的应用
CMD ["python", "app.py"]
```

然后在运行时使用：
```bash
docker exec -it <container_id> ssh user@host
```

#### 方案 3：使用多阶段构建和 SSH 转发

```dockerfile
# 构建阶段
FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# 使用 SSH 下载私有依赖（可选）
RUN --mount=type=ssh pip install -r requirements.txt

# 运行阶段
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app .

CMD ["python", "app.py"]
```

使用时：
```bash
docker build --ssh default=$SSH_AUTH_SOCK -t myapp .
```

## 架构对比

### ❌ 错误的架构
```
┌─────────────────┐
│  Docker Build   │
│                 │
│  RUN ssh-licco  │ ← ❌ MCP 服务器无法在此运行
│                 │
└─────────────────┘
```

### ✅ 正确的架构
```
┌──────────────────┐      ┌─────────────────┐
│  AI Client       │      │  Docker Build   │
│  (Trae/Cursor)   │      │                 │
│                  │      │  RUN apt-get    │
│  MCP Server ─────┼──────┤  install ssh    │
│  ssh-licco       │      │                 │
│                  │      │  docker exec    │
└──────────────────┘      └─────────────────┘
     宿主机运行                  容器内运行
```

## 最佳实践

### 1. **MCP 服务器定位**
- ✅ 作为开发工具运行在宿主机
- ✅ 与 AI 客户端配合使用
- ✅ 用于自动化 SSH 操作

### 2. **Docker 中使用 SSH**
- ✅ 安装 `openssh-client` 包
- ✅ 使用 `docker exec` 执行 SSH 命令
- ✅ 使用 `--mount=type=ssh` 进行 SSH 转发

### 3. **CI/CD 集成**
```yaml
# GitHub Actions 示例
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.5.3
        with:
          ssh-private-key: ${{ secrets.SSH_KEY }}
      
      - name: Build Docker
        run: docker build --ssh default -t myapp .
```

## 常见问题

### Q: 我可以让 MCP 服务器在 Docker 容器中运行吗？

A: 可以，但不推荐用于构建阶段。可以在运行时使用：

```dockerfile
FROM python:3.11-slim

RUN pip install ssh-licco

# 作为服务运行（需要特殊配置）
CMD ["ssh-licco"]
```

但这需要：
- 配置 Docker 的 stdin/stdout
- 使用 `docker run -it` 保持交互
- 处理信号和优雅关闭

### Q: 如何在 Kubernetes 中使用 MCP？

A: MCP 不适合在 Kubernetes Pod 中运行。建议：
1. 在开发环境使用 MCP
2. 在 K8s 中使用标准的 SSH 工具或 API

### Q: 能否在 GitHub Codespaces 中使用 MCP？

A: 可以！Codespaces 支持 MCP 服务器：
1. 安装 `ssh-licco`
2. 配置 MCP 客户端
3. 正常使用

## 总结

**核心要点：**
- ❌ 不要在 Docker 构建中运行 MCP 服务器
- ✅ 在宿主机运行 MCP，通过 AI 客户端操作 Docker
- ✅ 在容器内使用标准 SSH 客户端
- ✅ 使用 SSH 转发进行安全构建

MCP 服务器是**开发工具**，不是**构建工具**。
