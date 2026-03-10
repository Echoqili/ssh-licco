---
name: "ssh-mcp-dev"
description: "SSH MCP server development guide. Invoke when working on ssh-licco project, including setup, debugging, version management, Docker deployment, and releases."
---

# SSH MCP Server Development Guide

## Project Overview

- **Project Name**: ssh-licco
- **Description**: SSH Model Context Protocol Server - Enable SSH functionality for AI models
- **Repository**: https://github.com/Echoqili/ssh-licco
- **Current Version**: 0.1.6 (stored in `ssh_mcp/__init__.py`)

## Project Structure

```
ssh-mcp/
├── ssh_mcp/              # Main source code
│   ├── __init__.py      # Version info (main version file)
│   ├── server.py        # MCP server implementation
│   ├── config_manager.py
│   ├── session_manager.py
│   ├── connection_config.py
│   ├── clients/         # SSH client implementations
│   └── ...
├── config/               # Runtime configuration
│   ├── hosts.json       # SSH host configurations
│   └── client_config.json
├── Dockerfile           # Docker image build
├── pyproject.toml       # Package configuration
├── sync_version.py      # Version sync script
└── .github/workflows/
    └── pypi.yml         # PyPI release workflow
```

## Quick Commands

```bash
# Install in development mode
pip install -e . --user

# Run tests
python -m pytest

# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/* -u __token__ -p <TOKEN>

# View version
python -c "from ssh_mcp import __version__; print(__version__)"
```

## Version Management

### Update Version
```bash
# Bug fix (PATCH): python sync_version.py 1.0.1
# New feature (MINOR): python sync_version.py 1.1.0
# Breaking change (MAJOR): python sync_version.py 2.0.0

python sync_version.py 0.1.7
```

### Version Files (sync automatically)
- `ssh_mcp/__init__.py` - Main version file
- `pyproject.toml` - Auto-synced
- `VERSION` - Backup

### Release Process (Tag After Push)

**Standard Workflow:**
```bash
# Step 1: Update version files
python sync_version.py 0.1.7

# Step 2: Commit and push code
git add .
git commit -m "release: v0.1.7"
git push origin master

# Step 3: Create and push tag (AFTER code is pushed)
git tag v0.1.7
git push origin v0.1.7 --tags

# Step 4: Build and upload to PyPI
python -m build
python -m twine upload dist/*
```

**What `sync_version.py` does:**
1. ✅ Updates version in `ssh_mcp/__init__.py`
2. ✅ Updates version in `pyproject.toml`
3. ✅ Updates `VERSION` file
4. ℹ️ Shows next steps (manual git operations)

**Why Tag After Push:**
- ✅ Ensures code is successfully pushed first
- ✅ Tag points to committed code on remote
- ✅ Clear separation between code and tag
- ✅ Easy to rollback if needed

**Complete Release Checklist:**
```bash
# 1. Update version
python sync_version.py 0.1.7

# 2. Commit changes
git add .
git commit -m "release: v0.1.7"

# 3. Push code to GitHub
git push origin master

# 4. Create and push tag
git tag v0.1.7
git push origin v0.1.7 --tags

# 5. Build package
python -m build

# 6. Upload to PyPI
python -m twine upload dist/*

# 7. Create GitHub Release (optional)
# Go to GitHub -> Releases -> Create new release from tag v0.1.7
```

**Quick Release Script:**
```bash
# Create release.sh
cat > release.sh << 'EOF'
#!/bin/bash
VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: ./release.sh <version>"
    exit 1
fi

python sync_version.py $VERSION
git add .
git commit -m "release: v$VERSION"
git push origin master
git tag v$VERSION
git push origin v$VERSION --tags
python -m build
python -m twine upload dist/*
echo "✅ Release v$VERSION complete!"
EOF

chmod +x release.sh

# Usage: ./release.sh 0.1.7
```

## Docker Configuration

### Build Docker Image

```bash
# Basic build
docker build -t ssh-licco:latest .

# Build with custom tag
docker build -t ssh-licco:0.1.6 .

# Build with Chinese mirrors (faster in China)
docker build --build-arg DOCKER_MIRRORS='["https://docker.mirrors.sjtug.sjtu.edu.cn","https://mirror.aliyuncs.com"]' -t ssh-licco:latest .
```

### Docker Image Tags

```bash
# Tag for latest
docker tag ssh-licco:latest your-registry/ssh-licco:latest

# Tag for version
docker tag ssh-licco:0.1.6 your-registry/ssh-licco:0.1.6
```

### Push to Registry

```bash
# Push to Docker Hub
docker push your-username/ssh-licco:latest

# Push to custom registry
docker push your-registry/ssh-licco:0.1.6
```

### Run Docker Container

```bash
# Run with environment variables
docker run -d \
  -e SSH_HOST=192.168.1.100 \
  -e SSH_USER=root \
  -e SSH_PASSWORD=your_password \
  ssh-licco:latest

# Run with config file mounted
docker run -d \
  -v $(pwd)/config:/app/config \
  -e SSH_HOST=192.168.1.100 \
  ssh-licco:latest
```

### Docker Compose

```yaml
version: '3.8'
services:
  ssh-mcp:
    build: .
    image: ssh-licco:latest
    environment:
      - SSH_HOST=192.168.1.100
      - SSH_USER=root
      - SSH_PASSWORD=${SSH_PASSWORD}
      - SSH_TIMEOUT=120
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

### Docker Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `DOCKER_MIRRORS` | 14 Chinese mirrors | Docker registry mirrors |

### Multi-stage Build Optimization

The Dockerfile uses multi-stage builds:
1. **Builder stage**: Install dependencies in venv
2. **Runtime stage**: Minimal runtime with only SSH client

Benefits:
- Smaller image size (~150MB vs ~1GB)
- Faster deployment
- Better security (non-root user)

## MCP Tools

Available tools:
- `ssh_config` - Configure SSH connection
- `ssh_connect` - Connect to SSH server
- `ssh_execute` - Execute remote command
- `ssh_disconnect` - Close connection
- `ssh_list_hosts` - List configured servers
- `ssh_add_host` - Add new server to config
- `ssh_remove_host` - Remove server from config
- `ssh_generate_key` - Generate SSH key pair
- `ssh_file_transfer` - Upload/download files
- `ssh_docker_build` - Build Docker image remotely
- `ssh_docker_status` - Check Docker status

## Configuration Priority

1. **MCP Config** (mcp.json env) - Highest
2. **Local Config** (config/hosts.json)
3. **User Parameters** - Lowest

## MCP Tool Usage Priority

**Golden Rule: ALWAYS prefer MCP tools over direct commands for ANY operation**

### Universal Priority Order (High to Low)

1. **MCP Tools (Any MCP)** - ⭐⭐⭐⭐⭐
   - **SSH MCP**: ssh_execute, ssh_docker_build, ssh_file_transfer, etc.
   - **GitHub MCP**: github_create_issue, github_create_pull, github_search_repos, etc.
   - **Other MCPs**: Any available MCP server tools
   - ✅ Use for ALL operations when available
   - ✅ Automatically handles authentication, connection management
   - ✅ Built-in error handling and retry logic
   - ✅ Centralized configuration and audit logging

2. **Native Commands** - ⭐⭐
   - Docker commands (docker build, docker run)
   - Git commands (git push, git commit)
   - System commands
   - ⚠️ Use ONLY when no MCP tool is available
   - ⚠️ Requires manual configuration and error handling

3. **Manual/Alternative Methods** - ⭐
   - Direct API calls
   - Custom scripts
   - Web interface operations
   - ❌ Last resort when MCP and native commands both unavailable

### Why Use MCP Tools?

✅ **Benefits:**
- Automatic connection pooling and authentication
- Built-in error handling and retry logic
- Centralized configuration management
- Audit logging for all operations
- Consistent interface across operations
- Better security (no credentials exposure in logs)
- Type-safe with proper error messages
- Community-maintained and tested

❌ **Without MCP Tools:**
- Manual connection and auth management
- Inconsistent error handling
- No audit trail
- Security risks (credentials in scripts/logs)
- Configuration duplication
- Fragile custom implementations

### Decision Flow

```
Start Operation
    ↓
Is there an MCP tool? ──YES──→ Use MCP Tool ✅
    ↓ NO
Can use native command? ──YES──→ Use Native Command ⚠️
    ↓ NO
Find alternative method ❌
    (API call, script, manual)
```

### Example Usage

**✅ Recommended (MCP Tools - Any MCP):**

```python
# SSH MCP - Remote operations
result = await ssh_execute(
    command="docker build -t ssh-licco:latest .",
    host="production-server"
)

# GitHub MCP - Repository operations  
issue = await github_create_issue(
    owner="Echoqili",
    repo="ssh-licco",
    title="Release v0.1.7",
    labels="release,enhancement"
)

# Multiple MCPs - Combined workflow
await ssh_file_transfer(file="dist/*.whl", target="/app/")
await github_create_release(tag="v0.1.7", notes="New release")
```

**⚠️ Acceptable (Native Commands - No MCP available):**

```bash
# Only when no MCP tool exists
git commit -m "feat: add new feature"
docker build -t ssh-licco:latest .
```

**❌ Avoid (Direct Methods - Last resort):**

```bash
# Don't use if MCP exists
ssh root@server "command"                    # → Use ssh_execute
curl -X POST api.github.com/repos/...     # → Use github_* MCP
echo "password" | sudo -S command         # → Use MCP with stored config
```

### Integration with Development Workflow

```
Task Category              → Preferred Tool
─────────────────────────────────────────────────────
Remote Server Operations  → SSH MCP Tools
   - Docker Build          → ssh_docker_build
   - File Transfer         → ssh_file_transfer
   - Command Execution     → ssh_execute
   - Status Check          → ssh_docker_status

GitHub Operations         → GitHub MCP Tools
   - Create Issue          → github_create_issue
   - Create PR             → github_create_pull
   - Search Repos          → github_search_repos
   - Manage Releases       → github_create_release

Local Development         → Native Commands
   - Git Operations        → git commit, git push
   - Docker Build (local)  → docker build
   - Testing              → pytest, python

Emergency/Fallback        → Manual Methods
   - Direct API calls      → curl, requests
   - Web interface         → Browser operations
   - Custom scripts        → Last resort
```

### MCP Tool Discovery

When starting a new task, always check for available MCP tools:

1. **Check MCP Servers**: What MCP servers are configured?
   - SSH MCP (ssh-licco)
   - GitHub MCP
   - Other MCPs...

2. **List Available Tools**: What tools does each MCP provide?
   - Review tool documentation
   - Check tool capabilities

3. **Choose Best Tool**: Select the most appropriate MCP tool
   - Prefer specialized MCP tools over generic ones
   - Consider error handling and logging features

4. **Fallback Strategy**: If no MCP tool available
   - Try native commands
   - Then consider custom scripts
   - Document the gap for future MCP development

## MCP Configuration Example

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_PORT": "22",
        "SSH_TIMEOUT": "120"
      }
    }
  }
}
```

## Common Issues

### Password Special Characters
Passwords with special characters work fine in JSON - no escaping needed.

### SSH Connection Failed
- Check server SSH service: `sudo systemctl status sshd`
- Restart if needed: `sudo systemctl restart sshd`

### Version Not Updated
- Restart Trae IDE after updating
- Or restart MCP server process

### Docker Build Failed
- Check Docker daemon is running: `docker info`
- Try with Chinese mirrors if in China
- Check disk space

### Docker Image Too Large
- Use multi-stage build (already optimized)
- Clean up cache: `docker builder prune`

## Development Workflow

1. **Make changes** to source code in `ssh_mcp/`
2. **Test locally**: `pip install -e . --user`
3. **Update version**: `python sync_version.py x.x.x`
4. **Build package**: `python -m build`
5. **Build Docker**: `docker build -t ssh-licco:x.x.x .`
6. **Release**: Upload to PyPI + Docker Hub + GitHub Release
7. **Document**: Update CHANGELOG.md

## Key Files Reference

| File | Purpose |
|------|---------|
| `ssh_mcp/__init__.py` | Version (main) |
| `ssh_mcp/server.py` | MCP server logic |
| `config/hosts.json` | Saved SSH hosts |
| `pyproject.toml` | Package config |
| `Dockerfile` | Docker image build |
| `VERSION_MANAGEMENT.md` | Version guide |
| `MCP_SETUP_GUIDE.md` | MCP setup |
| `PASSWORD_SECURITY.md` | Security features |

## Testing MCP Tools

```python
from ssh_mcp import SSHMCPServer
import asyncio

async def test():
    server = SSHMCPServer()
    # Use server.server methods...

asyncio.run(test())
```
