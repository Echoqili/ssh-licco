---
name: "ssh-mcp-dev"
description: "SSH MCP server development guide. Invoke when working on ssh-licco project, including setup, debugging, version management, Docker deployment, and releases."
---

# SSH MCP Server Development Guide

## Project Overview

- **Project Name**: ssh-licco
- **Description**: SSH Model Context Protocol Server - Enable SSH functionality for AI models
- **Repository**: https://github.com/Echoqili/ssh-licco
- **Current Version**: 0.1.7 (stored in `ssh_mcp/__init__.py`)

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
│   │   ├── paramiko_client.py
│   │   ├── asyncssh_client.py
│   │   └── fabric_client.py
│   └── ...
├── config/               # Runtime configuration
│   ├── hosts.json       # SSH host configurations
│   ├── mcp.user.config.json.example
│   ├── mcp.presets.json
│   └── CONFIG_GUIDE.md
├── Dockerfile           # Docker image build
├── pyproject.toml       # Package configuration
├── sync_version.py      # Version sync script
├── .github/workflows/
│   └── pypi.yml         # PyPI release workflow
└── .trae/skills/
    └── ssh-mcp-dev/
        └── SKILL.md     # This skill file
```

## Git Workflow

### Always create a new branch for changes

```bash
# 1. Update local master
git checkout master
git pull origin master

# 2. Create a new branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description

# 3. Make your changes
# ... edit files ...

# 4. Commit your changes
git add -A
git commit -m "feat: add new feature"

# 5. Push to remote
git push -u origin feature/your-feature-name

# 6. Create Pull Request on GitHub
# Go to https://github.com/Echoqili/ssh-licco and create PR

# 7. After PR is merged, update local master
git checkout master
git pull origin master
```

### Branch Naming Conventions

| Type | Example | Use Case |
|------|---------|----------|
| `feature/` | `feature/add-server-management` | New features |
| `fix/` | `fix/password-display-issue` | Bug fixes |
| `docs/` | `docs/update-readme` | Documentation |
| `refactor/` | `refactor/improve-code` | Code improvements |

### Commit Message Format

```
<type>: <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `chore`: Maintenance
- `test`: Testing

Examples:
```
feat: add ssh_list_hosts tool
fix: hide password in MCP responses
docs: update version management guide
chore: bump version to 0.1.7
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

python sync_version.py 0.1.8
```

### Version Files (sync automatically)
- `ssh_mcp/__init__.py` - Main version file
- `pyproject.toml` - Auto-synced
- `VERSION` - Backup

### Release Process
1. Update version: `python sync_version.py x.x.x`
2. Build: `python -m build`
3. Upload: `python -m twine upload dist/*`
4. Create GitHub Release: `git tag vx.x.x && git push origin vx.x.x`

## Docker Configuration

### Build Docker Image

```bash
# Basic build
docker build -t ssh-licco:latest .

# Build with custom tag
docker build -t ssh-licco:0.1.7 .

# Build with Chinese mirrors (faster in China)
docker build --build-arg DOCKER_MIRRORS='["https://docker.mirrors.sjtug.sjtu.edu.cn","https://mirror.aliyuncs.com"]' -t ssh-licco:latest .
```

### Docker Image Tags

```bash
# Tag for latest
docker tag ssh-licco:latest your-registry/ssh-licco:latest

# Tag for version
docker tag ssh-licco:0.1.7 your-registry/ssh-licco:0.1.7
```

### Push to Registry

```bash
# Push to Docker Hub
docker push your-username/ssh-licco:latest

# Push to custom registry
docker push your-registry/ssh-licco:0.1.7
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

## SSH Client Types

### Configuration

Set `SSH_CLIENT_TYPE` environment variable:
- `common` (default) - paramiko (stable, recommended)
- `performance` - asyncssh (high performance)
- `development` - fabric (simple API)

### Configuration Priority

1. **MCP Config** (mcp.json env) - Highest
2. **Local Config** (config/hosts.json)
3. **User Parameters** - Lowest

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
        "SSH_TIMEOUT": "120",
        "SSH_CLIENT_TYPE": "common"
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

## Development Workflow (Complete)

1. **Create branch** from master
   ```bash
   git checkout master
   git pull origin master
   git checkout -b feature/your-feature
   ```

2. **Make changes** to source code in `ssh_mcp/`

3. **Test locally**
   ```bash
   pip install -e . --user
   # test your changes
   ```

4. **Commit and push**
   ```bash
   git add -A
   git commit -m "feat: your feature"
   git push -u origin feature/your-feature
   ```

5. **Create Pull Request** on GitHub

6. **After PR merged**:
   - Update version: `python sync_version.py x.x.x`
   - Build: `python -m build`
   - Upload to PyPI: `python -m twine upload dist/*`
   - Create GitHub Release: `git tag vx.x.x && git push origin vx.x.x`

7. **Update local master**
   ```bash
   git checkout master
   git pull origin master
   ```

## Key Files Reference

| File | Purpose |
|------|---------|
| `ssh_mcp/__init__.py` | Version (main) |
| `ssh_mcp/server.py` | MCP server logic |
| `config/hosts.json` | Saved SSH hosts |
| `config/mcp.user.config.json` | User configuration |
| `config/mcp.presets.json` | SSH client type presets |
| `config/CONFIG_GUIDE.md` | Configuration guide |
| `pyproject.toml` | Package config |
| `Dockerfile` | Docker image build |
| `sync_version.py` | Version sync script |
| `.trae/skills/ssh-mcp-dev/SKILL.md` | This skill |

## Documentation Reference

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `USAGE.md` | Detailed usage guide |
| `VERSION_MANAGEMENT.md` | Version management and release process |
| `COMPLETE_SECURITY_FIXES.md` | Security fixes and best practices |
| `docs/API_REFERENCE.md` | API documentation |
| `docs/CONTRIBUTING.md` | Contribution guidelines |

## Testing MCP Tools

```python
from ssh_mcp import SSHMCPServer
import asyncio

async def test():
    server = SSHMCPServer()
    # Use server.server methods...

asyncio.run(test())
```
