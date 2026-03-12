# 🔒 SSH LICCO 安全改进计划

## 📊 当前安全评分：0.5/1.0（严重风险）

---

## ⚠️ 发现的安全问题

### 1. 硬编码密码（Hardcoded Passwords）
**严重级别**: 🔴 高

**问题描述**:
- 代码中可能存在硬编码的密码
- 配置文件包含明文密码
- 示例代码中有真实凭证

**影响**:
- 攻击者可以获取密码
- 可能导致未授权访问
- 供应链攻击风险

**解决方案**:

#### ✅ 立即修复
1. **移除所有硬编码密码**
   ```python
   # ❌ 错误示例
   password = "admin123"
   
   # ✅ 正确做法
   import os
   password = os.getenv('SSH_PASSWORD')
   ```

2. **使用环境变量**
   ```python
   # 从环境变量获取
   SSH_HOST = os.getenv('SSH_HOST')
   SSH_USER = os.getenv('SSH_USER')
   SSH_PASSWORD = os.getenv('SSH_PASSWORD')
   ```

3. **添加 .env 示例文件**
   ```bash
   # .env.example
   SSH_HOST=192.168.1.100
   SSH_USER=root
   SSH_PASSWORD=your_password_here
   SSH_PORT=22
   ```

4. **更新 .gitignore**
   ```gitignore
   # 敏感信息
   .env
   *.pem
   *.key
   credentials.json
   ```

---

### 2. 不安全的命令执行（Unsafe Command Execution）
**严重级别**: 🔴 高

**问题描述**:
- 用户输入直接用于命令执行
- 缺少输入验证和清理
- 可能存在命令注入风险

**影响**:
- 远程代码执行
- 服务器被入侵
- 数据泄露

**解决方案**:

#### ✅ 立即修复
1. **输入验证**
   ```python
   # ❌ 危险代码
   def execute_command(cmd):
       os.system(cmd)
   
   # ✅ 安全做法
   import shlex
   import subprocess
   
   def execute_command(cmd):
       # 验证命令白名单
       allowed_commands = ['ls', 'cd', 'pwd', 'cat', 'grep']
       cmd_parts = shlex.split(cmd)
       
       if cmd_parts[0] not in allowed_commands:
           raise ValueError(f"Command '{cmd_parts[0]}' not allowed")
       
       # 使用 subprocess 而不是 os.system
       result = subprocess.run(
           cmd_parts,
           capture_output=True,
           text=True,
           timeout=30
       )
       return result.stdout
   ```

2. **命令白名单**
   ```python
   ALLOWED_COMMANDS = {
       'ls', 'dir', 'cd', 'pwd', 'cat', 'grep',
       'docker', 'systemctl', 'top', 'ps', 'free'
   }
   
   def validate_command(cmd):
       base_cmd = cmd.split()[0] if cmd.split() else ''
       if base_cmd not in ALLOWED_COMMANDS:
           raise SecurityError(f"Command not allowed: {base_cmd}")
   ```

3. **参数化查询**
   ```python
   # ❌ 危险
   cmd = f"ls -la {user_input}"
   os.system(cmd)
   
   # ✅ 安全
   cmd = ['ls', '-la', user_input]
   subprocess.run(cmd, check=True)
   ```

---

### 3. 过宽的文件系统访问（Overly Broad Filesystem Access）
**严重级别**: 🟡 中

**问题描述**:
- 可以访问任意文件路径
- 缺少路径限制
- 可能导致目录遍历攻击

**影响**:
- 敏感文件泄露（/etc/passwd, ~/.ssh/id_rsa）
- 未授权文件修改
- 系统配置泄露

**解决方案**:

#### ✅ 立即修复
1. **路径限制**
   ```python
   from pathlib import Path
   import os
   
   class SecureFileManager:
       def __init__(self, base_dir='/home/user'):
           self.base_dir = Path(base_dir).resolve()
       
       def safe_path(self, user_path):
           """验证并返回安全路径"""
           full_path = (self.base_dir / user_path).resolve()
           
           # 确保路径在 base_dir 内
           if not str(full_path).startswith(str(self.base_dir)):
               raise SecurityError("Path traversal detected!")
           
           return full_path
   ```

2. **访问控制**
   ```python
   # 禁止访问的目录
   FORBIDDEN_PATHS = [
       '/etc', '/root', '/boot', '/proc', '/sys'
   ]
   
   def is_path_allowed(path):
       path_str = str(path)
       for forbidden in FORBIDDEN_PATHS:
           if path_str.startswith(forbidden):
               return False
       return True
   ```

3. **文件权限检查**
   ```python
   def check_file_permissions(filepath):
       """检查文件权限"""
       stat_info = os.stat(filepath)
       mode = stat_info.st_mode
       
       # 检查是否 world-writable
       if mode & stat.S_IWOTH:
           raise SecurityError("File is world-writable!")
       
       return True
   ```

---

### 4. 依赖项漏洞（Dependency Vulnerabilities）
**严重级别**: 🟡 中

**问题描述**:
- 4 个已知漏洞（0 严重，3 高危）
- 1 个包验证问题

**影响**:
- 供应链攻击
- 已知漏洞利用
- 安全风险传递

**解决方案**:

#### ✅ 立即修复
1. **更新依赖**
   ```bash
   # 检查过时的包
   pip list --outdated
   
   # 更新所有包
   pip install --upgrade asyncssh cryptography
   
   # 使用 pip-audit 检查漏洞
   pip install pip-audit
   pip-audit
   ```

2. **固定版本**
   ```toml
   # pyproject.toml
   [project]
   dependencies = [
       "asyncssh>=2.18.0,<3.0.0",
       "cryptography>=42.0.0,<43.0.0",
   ]
   ```

3. **定期扫描**
   ```bash
   # 使用 safety 检查
   pip install safety
   safety check
   
   # 使用 pip-audit
   pip-audit -r requirements.txt
   ```

---

## 📋 安全检查清单

### 🔐 代码安全

- [ ] 移除所有硬编码密码
- [ ] 使用环境变量管理敏感信息
- [ ] 添加 .env.example 文件
- [ ] 更新 .gitignore
- [ ] 实现命令白名单
- [ ] 添加输入验证
- [ ] 使用参数化查询
- [ ] 实现路径限制
- [ ] 添加文件权限检查

### 📦 依赖安全

- [ ] 更新所有依赖到最新版本
- [ ] 固定依赖版本范围
- [ ] 运行 pip-audit 扫描
- [ ] 移除未使用的依赖
- [ ] 使用可信源

### 🔒 配置安全

- [ ] 添加安全配置文档
- [ ] 实现日志审计
- [ ] 添加速率限制
- [ ] 实现会话超时
- [ ] 添加错误处理

### 📝 文档安全

- [ ] 更新安全文档
- [ ] 添加安全最佳实践
- [ ] 提供配置示例
- [ ] 说明权限需求
- [ ] 添加警告信息

---

## 🚀 实施步骤

### 阶段 1：立即修复（1-2 小时）

1. **搜索并移除硬编码密码**
   ```bash
   # 搜索可能的密码
   grep -r "password.*=" . --include="*.py"
   grep -r "passwd.*=" . --include="*.py"
   grep -r "secret.*=" . --include="*.py"
   ```

2. **添加输入验证**
   - 所有用户输入都要验证
   - 实现命令白名单

3. **更新依赖**
   ```bash
   pip install --upgrade asyncssh cryptography
   pip-audit
   ```

### 阶段 2：代码审查（2-4 小时）

1. **审查所有命令执行**
   - 检查 os.system() 调用
   - 检查 subprocess 调用
   - 添加验证

2. **审查文件访问**
   - 检查所有文件操作
   - 添加路径限制
   - 实现权限检查

3. **添加安全测试**
   - 编写安全测试用例
   - 测试命令注入
   - 测试路径遍历

### 阶段 3：文档和配置（1 小时）

1. **更新文档**
   - 添加安全说明
   - 提供配置示例
   - 说明最佳实践

2. **配置示例**
   ```python
   # config.example.py
   import os
   
   # 从环境变量获取
   SSH_HOST = os.getenv('SSH_HOST', 'localhost')
   SSH_USER = os.getenv('SSH_USER', 'root')
   SSH_PASSWORD = os.getenv('SSH_PASSWORD')  # 必须设置
   SSH_PORT = int(os.getenv('SSH_PORT', '22'))
   
   # 安全配置
   ALLOWED_COMMANDS = ['ls', 'cd', 'pwd', 'cat']
   MAX_SESSION_TIMEOUT = 7200  # 2 小时
   ```

---

## 📊 预期改进

### 修复前
- **安全评分**: 0.5/1.0
- **风险等级**: Critical Risk
- **问题数**: 11 个

### 修复后（预期）
- **安全评分**: 0.8-0.9/1.0
- **风险等级**: Low Risk
- **问题数**: 2-3 个

---

## 🎯 快速修复脚本

### 1. 扫描硬编码密码
```bash
#!/bin/bash
# scan_secrets.sh

echo "Scanning for hardcoded secrets..."

# 搜索密码
grep -rn "password\s*=\s*['\"]" . --include="*.py"
grep -rn "passwd\s*=\s*['\"]" . --include="*.py"
grep -rn "secret\s*=\s*['\"]" . --include="*.py"

# 搜索 API key
grep -rn "api_key\s*=\s*['\"]" . --include="*.py"
grep -rn "apikey\s*=\s*['\"]" . --include="*.py"

echo "Scan complete!"
```

### 2. 检查依赖漏洞
```bash
#!/bin/bash
# check_deps.sh

echo "Checking dependencies..."

# 安装工具
pip install pip-audit safety

# 扫描
echo "Running pip-audit..."
pip-audit

echo "Running safety check..."
safety check

echo "Check complete!"
```

---

## 📞 需要帮助？

### 安全资源
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)
- [AsyncSSH Security](https://asyncssh.readthedocs.io/en/latest/security.html)

### 工具推荐
- **pip-audit**: 依赖漏洞扫描
- **safety**: Python 包安全检查
- **bandit**: Python 安全 lint 工具
- **semgrep**: 代码安全分析

---

## 🎊 总结

### 当前问题
- ❌ 硬编码密码
- ❌ 不安全命令执行
- ❌ 过宽文件访问
- ❌ 依赖漏洞

### 修复优先级
1. 🔴 **立即**: 移除硬编码密码
2. 🔴 **立即**: 添加输入验证
3. 🟡 **本周**: 更新依赖
4. 🟡 **本周**: 实现路径限制

### 预期结果
- ✅ 安全评分提升到 0.8+
- ✅ 风险等级降低到 Low
- ✅ 用户信任度提升
- ✅ 更好的市场接受度

---

**立即开始修复，提升安全评分！** 🚀

*Generated: 2026-03-12*  
*Current Score: 0.5*  
*Target Score: 0.8+*
