# 贡献指南

感谢你对 SSH LICCO 项目的关注！欢迎贡献代码、报告问题或提出建议。

## 目录

- [行为准则](#行为准则)
- [贡献方式](#贡献方式)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交流程](#提交流程)
- [测试要求](#测试要求)
- [文档规范](#文档规范)

---

## 行为准则

本项目采用 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化的语言或图像
- 人身攻击或侮辱性评论
- 公开或私下骚扰
- 未经许可发布他人信息
- 其他不道德或不专业的行为

---

## 贡献方式

### 1. 报告 Bug

发现 Bug？请创建 Issue 并提供：

- 清晰的标题和描述
- 重现步骤
- 预期行为和实际行为
- 环境信息（Python 版本、操作系统等）
- 相关日志或截图

### 2. 提出新功能

有新想法？请创建 Issue 并说明：

- 功能描述
- 使用场景
- 实现思路（可选）
- 潜在影响

### 3. 提交代码

准备好贡献代码？请遵循以下流程：

1. Fork 仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

### 4. 改进文档

文档同样重要！欢迎：

- 修正拼写和语法错误
- 补充缺失的说明
- 添加示例代码
- 翻译文档

---

## 开发环境设置

### 1. Fork 和克隆

```bash
# Fork 仓库
# 在 GitHub 上点击 Fork 按钮

# 克隆到本地
git clone https://github.com/YOUR_USERNAME/ssh-licco.git
cd ssh-licco

# 添加上游仓库
git remote add upstream https://github.com/Echoqili/ssh-licco.git
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 或使用
pip install -r requirements-dev.txt
```

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_session_manager.py

# 查看测试覆盖率
pytest --cov=ssh_mcp --cov-report=html
```

---

## 代码规范

### Python 代码风格

遵循 [PEP 8](https://pep8.org/) 和 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。

```python
# ✅ 好的示例
from typing import Optional

class SSHConnection:
    """SSH 连接管理类."""
    
    def __init__(self, host: str, port: int = 22):
        """初始化连接.
        
        Args:
            host: 主机名或 IP
            port: 端口号，默认 22
        """
        self.host = host
        self.port = port
        self._connected = False
    
    def connect(self, timeout: int = 30) -> bool:
        """建立连接."""
        # 实现代码
        pass
```

```python
# ❌ 不好的示例
class sshConnection:  # 类名应该用大驼峰
    def __init__(self,host,port=22):  # 缺少空格
        self.host=host  # 缺少空格
        self.p=port  # 变量名不清晰
```

### 类型注解

所有公共 API 必须使用类型注解：

```python
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ConnectionConfig:
    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    timeout: int = 30

def execute_command(
    session_id: str,
    command: str,
    timeout: int = 30
) -> Dict[str, any]:
    """执行命令."""
    pass
```

### 错误处理

使用自定义异常类：

```python
from ssh_mcp.exceptions import SSHException, ConnectionException

def connect(config: ConnectionConfig) -> SessionInfo:
    try:
        # 连接代码
        pass
    except TimeoutError as e:
        raise ConnectionException(
            message="连接超时",
            host=config.host,
            port=config.port,
            original_exception=e
        ) from e
```

### 日志记录

使用标准日志接口：

```python
from ssh_mcp.logging_config import get_logger

logger = get_logger(__name__)

def process_command(command: str) -> str:
    logger.debug(f"处理命令：{command}")
    try:
        result = execute(command)
        logger.info(f"命令执行成功")
        return result
    except Exception as e:
        logger.error(f"命令执行失败：{e}", exc_info=True)
        raise
```

---

## 提交流程

### 1. 创建分支

```bash
# 从主分支创建特性分支
git checkout -b feature/your-feature-name

# 或修复 bug
git checkout -b fix/issue-123
```

**分支命名规范：**

- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关
- `chore/xxx` - 构建/工具相关

### 2. 提交更改

```bash
# 添加更改
git add .

# 提交（遵循约定式提交规范）
git commit -m "feat: 添加 SSH 密钥管理功能"
git commit -m "fix: 修复连接超时问题"
git commit -m "docs: 更新 API 文档"
```

**提交信息格式：**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型说明：**

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例：**

```
feat(session): 添加会话保活功能

- 实现自动心跳包发送
- 支持配置保活间隔
- 添加会话超时检测

Closes #123
```

### 3. 推送分支

```bash
# 推送到远程
git push origin feature/your-feature-name
```

### 4. 创建 Pull Request

1. 在 GitHub 上访问你的 fork
2. 点击 "Compare & pull request"
3. 填写 PR 描述
4. 等待代码审查

**PR 描述模板：**

```markdown
## 描述
简要描述此 PR 的目的

## 相关 Issue
Closes #123

## 更改类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化

## 测试
- [ ] 已添加单元测试
- [ ] 已添加集成测试
- [ ] 所有测试通过

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已添加类型注解
- [ ] 已更新文档
- [ ] 无新的警告信息
```

---

## 测试要求

### 单元测试

所有新功能必须包含单元测试：

```python
# tests/test_connection.py
import pytest
from ssh_mcp import ConnectionConfig, get_ssh_service

class TestConnection:
    def test_connection_config_default(self):
        """测试默认配置."""
        config = ConnectionConfig(host="example.com")
        assert config.port == 22
        assert config.timeout == 30
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """测试连接成功."""
        service = get_ssh_service()
        config = ConnectionConfig(
            host="test.example.com",
            username="test",
            password="test"
        )
        
        info = service.connect(config)
        assert info.session_id is not None
        assert info.host == "test.example.com"
    
    @pytest.mark.asyncio
    asyncio
    async def test_connect_invalid_credentials(self):
        """测试无效凭据."""
        service = get_ssh_service()
        config = ConnectionConfig(
            host="test.example.com",
            username="invalid",
            password="wrong"
        )
        
        with pytest.raises(AuthenticationException):
            service.connect(config)
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_connection.py

# 运行特定测试类
pytest tests/test_connection.py::TestConnection

# 运行特定测试方法
pytest tests/test_connection.py::TestConnection::test_connect_success

# 查看覆盖率
pytest --cov=ssh_mcp --cov-report=term-missing

# 生成 HTML 报告
pytest --cov=ssh_mcp --cov-report=html:coverage_report
```

### 代码质量检查

```bash
# 代码格式化检查
ruff check ssh_mcp tests

# 自动格式化
ruff format ssh_mcp tests

# 类型检查
mypy ssh_mcp

# 导入排序
isort ssh_mcp tests
```

---

## 文档规范

### 代码注释

所有公共函数和类必须有文档字符串：

```python
class SSHService:
    """SSH 服务层，提供完整的会话管理功能."""
    
    def connect(self, config: ConnectionConfig) -> SessionInfo:
        """建立 SSH 连接.
        
        Args:
            config: SSH 连接配置
            
        Returns:
            会话信息对象
            
        Raises:
            ConnectionException: 连接失败时
            AuthenticationException: 认证失败时
            
        Example:
            >>> service = get_ssh_service()
            >>> config = ConnectionConfig(host="example.com")
            >>> info = service.connect(config)
            >>> print(info.session_id)
        """
        pass
```

### 文档更新

更新代码时同步更新文档：

1. 更新 docstring
2. 更新相关 Markdown 文档
3. 添加示例代码
4. 更新 CHANGELOG.md

### 文档构建

```bash
# 安装文档工具
pip install mkdocs mkdocs-material

# 本地预览文档
cd docs
mkdocs serve

# 构建文档
mkdocs build
```

---

## 代码审查流程

### 审查标准

审查者会关注：

1. **代码质量**
   - 遵循代码规范
   - 类型注解完整
   - 错误处理完善
   - 日志记录适当

2. **功能正确性**
   - 实现符合需求
   - 边界条件处理
   - 性能考虑

3. **测试覆盖**
   - 单元测试完整
   - 测试用例合理
   - 覆盖率达标

4. **文档完整性**
   - 代码注释清晰
   - 文档更新同步
   - 示例代码正确

### 审查反馈

收到审查意见后：

1. 及时回复
2. 根据意见修改
3. 重新提交
4. 请求重新审查

### 合并代码

代码审查通过后：

1. 确保所有测试通过
2. 确保无冲突
3. 由维护者合并到主分支
4. 删除特性分支

---

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

- `MAJOR.MINOR.PATCH` (如 1.2.3)
- `MAJOR`: 不兼容的 API 更改
- `MINOR`: 向后兼容的功能添加
- `PATCH`: 向后兼容的 Bug 修复

### 发布检查清单

发布前确保：

- [ ] 所有测试通过
- [ ] 代码覆盖率>80%
- [ ] 文档已更新
- [ ] CHANGELOG.md 已更新
- [ ] 版本号已更新
- [ ] 无已知严重 Bug

### 发布步骤

```bash
# 更新版本号
# 在 pyproject.toml 和 __init__.py 中

# 提交版本更新
git commit -m "chore: bump version to 0.2.0"

# 打标签
git tag -a v0.2.0 -m "Release version 0.2.0"

# 推送标签
git push origin v0.2.0

# 构建包
pip install build
python -m build

# 发布到 PyPI
pip install twine
twine upload dist/*
```

---

## 常见问题

### Q: 如何开始第一次贡献？

A: 从简单的任务开始：
1. 查看标记为 "good first issue" 的 Issue
2. 修复文档中的拼写错误
3. 添加测试用例
4. 改进注释

### Q: 提交后多久会被审查？

A: 通常 1-3 个工作日。如果超过一周未回复，可以 @ 维护者。

### Q: 可以同时提交多个 PR 吗？

A: 可以，但建议每个 PR 专注于一个功能或修复。

### Q: 如何联系维护者？

A: 可以通过以下方式：
- GitHub Issue
- GitHub Discussion
- 项目邮箱（如果有）

---

## 致谢

感谢所有贡献者！

[![Contributors](https://contrib.rocks/image?repo=Echoqili/ssh-licco)](https://github.com/Echoqili/ssh-licco/graphs/contributors)

---

## 相关资源

- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [PEP 8](https://pep8.org/)
- [Python Testing](https://docs.pytest.org/)
