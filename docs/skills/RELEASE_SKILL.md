# 🚀 ssh-licco 发布技能

## 📋 技能概述

这个技能帮助你完成 ssh-licco 项目的完整发布流程，包括代码提交、本地测试、打包发布等步骤。

---

## 🎯 适用场景

当你需要：
- ✅ 修复 bug 后发布新版本
- ✅ 添加新功能后发布
- ✅ 定期维护更新
- ✅ 紧急安全补丁

---

## 📝 完整发布流程

### 阶段 1：代码提交

#### 1.1 检查修改

```bash
git status
git diff <file>
```

#### 1.2 添加并提交

```bash
git add <files>
git commit -m "fix: 简短描述

详细说明（可选）"
```

#### 1.3 推送到 GitHub

```bash
git push github master
```

---

### 阶段 2：本地测试（⚠️ 必须）

#### 2.1 卸载旧版本

```bash
pip uninstall ssh-licco -y
```

#### 2.2 构建新版本

```bash
python -m build
```

#### 2.3 本地安装测试版

```bash
pip install --upgrade --user dist/ssh_licco-*.whl
```

#### 2.4 验证版本

```bash
python -c "import ssh_mcp; print(ssh_mcp.__version__)"
```

#### 2.5 功能测试

创建测试脚本 `test_release.py`：

```python
"""
发布前测试脚本
"""

from ssh_mcp.security import SecurityLevel, CommandValidator, PathValidator

print("🧪 测试新版本功能...")

# 测试安全模块
v = CommandValidator(security_level=SecurityLevel.BALANCED)
v.validate_command('ls -la')
print("✅ 命令验证通过")

# 测试路径验证
p = PathValidator(security_level=SecurityLevel.BALANCED)
path = p.validate_path('documents')
print(f"✅ 路径验证通过：{path}")

print("\n✅ 所有测试通过！")
```

运行测试：

```bash
python test_release.py
```

---

### 阶段 3：正式发布

#### 3.1 更新版本号

编辑 `pyproject.toml`：

```toml
[project]
version = "0.2.3"  # 递增版本号
```

#### 3.2 提交版本更新

```bash
git add pyproject.toml
git commit -m "chore: release v0.2.3 - Bug fix release

Fixes:
- Fix CommandValidator initialization order
- Prevent AttributeError on module load

Improvements:
- Add comprehensive test suite
- Improve error messages"
```

#### 3.3 创建 Git 标签

```bash
git tag v0.2.3
git push github master --tags
```

#### 3.4 构建发布包

```bash
python -m build
```

#### 3.5 上传到 PyPI

```bash
python -m twine upload dist/ssh_licco-0.2.3* --config-file .pypirc
```

#### 3.6 创建 GitHub Release

使用脚本 `create_release.py` 或手动创建：

```python
"""
创建 GitHub Release
"""

import requests

GITHUB_TOKEN = 'your_token'
GITHUB_OWNER = 'Echoqili'
GITHUB_REPO = 'ssh-licco'

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

release_data = {
    'tag_name': 'v0.2.3',
    'name': 'v0.2.3 - Bug Fix Release',
    'body': '''
## 🐛 Bug Fixes

- Fix CommandValidator initialization order
- Prevent AttributeError when loading security module

## ✅ Testing

All tests passed:
- BALANCED mode initialization
- RELAXED mode initialization  
- STRICT mode initialization
- Custom commands
- Path validation
- Environment variable configuration

## 🔗 Links

- PyPI: https://pypi.org/project/ssh-licco/0.2.3/
- MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco
''',
    'draft': False,
    'prerelease': False
}

response = requests.post(
    f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases',
    headers=headers,
    json=release_data,
    timeout=15
)

print(f"Release created: {response.json()['html_url']}")
```

#### 3.7 发布到 MCP Registry

使用脚本 `publish_mcp.py`：

```python
"""
发布到 MCP Registry
"""

import requests
import os

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
VERSION = "0.2.3"
PYPI_PACKAGE = "ssh-licco"
SERVER_NAME = "io.github.Echoqili/ssh-licco"

# 1. 获取 PyPI 信息
response = requests.get(
    f"https://pypi.org/pypi/{PYPI_PACKAGE}/{VERSION}/json",
    timeout=10
)
pypi_data = response.json()
description = pypi_data['info']['summary']

# 2. 登录 MCP Registry
response = requests.post(
    "https://registry.modelcontextprotocol.io/v0.1/auth/github-at",
    json={"github_token": GITHUB_TOKEN},
    timeout=10
)
access_token = response.json().get('registry_token')

# 3. 发布
publish_data = {
    "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
    "name": SERVER_NAME,
    "version": VERSION,
    "description": description,
    "repository": {
        "url": "https://github.com/Echoqili/ssh-licco.git",
        "source": "github"
    },
    "packages": [{
        "registryType": "pypi",
        "identifier": PYPI_PACKAGE,
        "version": VERSION,
        "runtimeHint": "python",
        "transport": {"type": "stdio"},
        "environmentVariables": [
            {
                "name": "SSH_SECURITY_LEVEL",
                "description": "Security level (strict/balanced/relaxed)",
                "default": "balanced"
            },
            {
                "name": "SSH_EXTRA_ALLOWED_COMMANDS",
                "description": "Extra allowed commands (comma-separated)"
            },
            {
                "name": "SSH_BASE_DIR",
                "description": "Base directory for path validation",
                "default": "/home"
            }
        ]
    }]
}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://registry.modelcontextprotocol.io/v0.1/publish",
    json=publish_data,
    headers=headers,
    timeout=15
)

if response.status_code == 200:
    print(f"✅ 发布成功！")
    print(f"   URL: https://registry.modelcontextprotocol.io/servers/{SERVER_NAME}")
else:
    print(f"❌ 发布失败：{response.status_code}")
```

---

### 阶段 4：验证发布

#### 4.1 检查 PyPI

访问：https://pypi.org/project/ssh-licco/0.2.3/

#### 4.2 检查 GitHub Release

访问：https://github.com/Echoqili/ssh-licco/releases/tag/v0.2.3

#### 4.3 检查 MCP Registry

访问：https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

#### 4.4 全新安装测试

```bash
# 在新环境或虚拟机中
pip install ssh-licco
python -c "import ssh_mcp; print(ssh_mcp.__version__)"
```

---

## 📋 发布检查清单

### 发布前

- [ ] 代码已提交并推送
- [ ] 本地测试通过
- [ ] 功能测试通过
- [ ] 版本号已更新
- [ ] CHANGELOG 已更新

### 发布中

- [ ] Git 标签已创建
- [ ] 包已构建
- [ ] PyPI 上传成功
- [ ] GitHub Release 创建
- [ ] MCP Registry 发布成功

### 发布后

- [ ] PyPI 页面显示正确
- [ ] GitHub Release 显示正确
- [ ] MCP Registry 显示正确
- [ ] 全新安装测试通过
- [ ] 文档已更新

---

## 🎯 快速发布脚本

创建 `quick_release.py`：

```python
"""
快速发布脚本
使用方法：python quick_release.py 0.2.3 "Bug fix release"
"""

import sys
import subprocess
import requests
import os

VERSION = sys.argv[1]
MESSAGE = sys.argv[2] if len(sys.argv) > 2 else "Release"

def run(cmd):
    """运行命令"""
    print(f"运行：{cmd}")
    subprocess.run(cmd, shell=True, check=True)

print("="*60)
print(f"🚀 发布 v{VERSION}")
print("="*60)

# 1. 更新版本号
print("\n1️⃣ 更新版本号...")
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = content.replace(f'version = "{VERSION.split(".")[0]}.{VERSION.split(".")[1]}.{int(VERSION.split(".")[2])-1}"', 
                         f'version = "{VERSION}"')
with open('pyproject.toml', 'w') as f:
    f.write(content)

# 2. 提交
print("\n2️⃣ 提交...")
run(f'git add pyproject.toml')
run(f'git commit -m "chore: release v{VERSION}"')

# 3. 打标签
print("\n3️⃣ 打标签...")
run(f'git tag v{VERSION}')
run(f'git push github master --tags')

# 4. 构建
print("\n4️⃣ 构建...")
run('python -m build')

# 5. 上传 PyPI
print("\n5️⃣ 上传 PyPI...")
run(f'python -m twine upload dist/ssh_licco-{VERSION}* --config-file .pypirc')

# 6. 完成
print("\n" + "="*60)
print(f"✅ v{VERSION} 发布完成！")
print("="*60)
print("\n📍 查看:")
print(f"   PyPI: https://pypi.org/project/ssh-licco/{VERSION}/")
print(f"   GitHub: https://github.com/Echoqili/ssh-licco/releases/tag/v{VERSION}")
```

---

## 💡 最佳实践

### 1. 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

- **MAJOR.MINOR.PATCH** (如 0.2.3)
- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的问题修复

### 2. 提交信息规范

```
fix: 修复问题
feat: 新增功能
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试
chore: 构建/工具
```

### 3. 测试原则

- ✅ 必须先本地测试
- ✅ 测试所有主要功能
- ✅ 测试边界情况
- ✅ 记录测试结果

### 4. 发布时机

- 📅 定期发布（如每 2 周）
- 🐛 紧急 bug 修复
- ✨ 重要功能完成
- 🔒 安全更新

---

## 📚 实战案例：v0.2.3 发布

### 背景

v0.2.2 版本发布后发现一个严重的初始化 bug，导致安全配置功能无法使用。

### Bug 描述

```python
# ❌ 错误的初始化顺序（v0.2.2）
class CommandValidator:
    def __init__(self, security_level):
        self._compile_patterns()  # 调用时 dangerous_patterns 还不存在
        self.dangerous_patterns = [...]  # 后设置
```

导致错误：
```
AttributeError: 'CommandValidator' object has no attribute 'dangerous_patterns'
```

### 修复方案

```python
# ✅ 正确的初始化顺序（v0.2.3）
class CommandValidator:
    def __init__(self, security_level):
        # 先设置 dangerous_patterns
        if security_level == SecurityLevel.STRICT:
            self.dangerous_patterns = self.DANGEROUS_PATTERNS_STRICT
        # ...
        
        # 再编译 patterns
        self._compile_patterns()
```

### 发布过程

#### 1. 评估影响
- **严重程度**: 高 🔴
- **影响版本**: v0.2.2
- **决定**: 发布 v0.2.3 紧急修复

#### 2. 本地测试
```python
from ssh_mcp.security import SecurityLevel, CommandValidator, PathValidator

# 测试所有模式
v = CommandValidator(security_level=SecurityLevel.BALANCED)
v.validate_command('ls -la')  # ✅

v = CommandValidator(security_level=SecurityLevel.RELAXED)
v.validate_command('git status')  # ✅

v = CommandValidator(security_level=SecurityLevel.STRICT)
v.validate_command('docker ps')  # ✅

p = PathValidator(security_level=SecurityLevel.BALANCED)
p.validate_path('documents')  # ✅
```

**结果**: 所有测试通过 ✅

#### 3. 提交流程
```bash
# 修复代码
git add ssh_mcp/security.py
git commit -m "fix: correct initialization order"
git push github master

# 发布新版本
git add pyproject.toml
git commit -m "chore: release v0.2.3 - Critical bug fix"
git tag v0.2.3
git push github master --tags
```

#### 4. 构建发布
```bash
python -m build
python -m twine upload dist/ssh_licco-0.2.3* --config-file .pypirc
```

#### 5. 创建 Release 和 MCP 发布
使用 `publish_v023.py` 脚本自动完成

### 结果

- ✅ GitHub Release: https://github.com/Echoqili/ssh-licco/releases/tag/v0.2.3
- ✅ PyPI: https://pypi.org/project/ssh-licco/0.2.3/
- ✅ MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

### 经验教训

1. **发布前必须本地测试** - 避免有 bug 的版本流出
2. **先测试再发布** - 不要跳过测试步骤
3. **文档与代码同步** - 及时更新文档
4. **自动化流程** - 使用脚本提高效率

---

## 🔗 相关资源

- [PyPI 文档](https://packaging.python.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [MCP Registry](https://modelcontextprotocol.io/)
- [Semantic Versioning](https://semver.org/)

---

## 📊 版本历史

| 版本 | 日期 | 主要变更 | 安全评分 |
|------|------|----------|----------|
| v0.2.3 | 2026-03-13 | 修复关键 bug | 预期 0.9+ ⭐⭐⭐ |
| v0.2.2 | 2026-03-13 | 安全配置增强（有 bug） | N/A |
| v0.2.1 | 2026-03-13 | 安全配置增强 | 0.8 ⭐⭐ |
| v0.2.0 | 2026-03-12 | 安全验证模块 | 0.7 ⭐⭐ |
| v0.1.7 | 2026-03-11 | 基础功能 | 0.5 🔴 |

---

**祝你发布顺利！** 🎉
