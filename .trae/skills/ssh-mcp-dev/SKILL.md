---
name: "ssh-mcp-dev"
description: "SSH MCP server development guide. Invoke when working on ssh-licco project, including setup, debugging, version management, Docker deployment, and releases."
---

# SSH MCP Server Development Guide

## Project Overview

- **Project Name**: ssh-licco
- **Description**: SSH Model Context Protocol Server - Enable SSH functionality for AI models
- **Repository**: https://github.com/Echoqili/ssh-licco
- **Current Version**: 0.5.5 (stored in `ssh_mcp/__init__.py`)
- **Python**: >=3.10, <3.14
- **License**: MIT

## Project Structure

```
ssh-mcp/
├── ssh_mcp/                    # Main source code
│   ├── __init__.py            # Version info (main version file)
│   ├── server.py              # MCP server implementation (SSHMCPServer)
│   ├── service.py             # SSH service protocol & connection info
│   ├── config_manager.py      # Config file management (hosts.json)
│   ├── session_manager.py     # SSH session lifecycle management
│   ├── connection_config.py   # Pydantic connection config model
│   ├── connection_pool.py     # Connection pool with health check
│   ├── executor.py            # Thread pool executor (async bridge)
│   ├── batch_executor.py      # Batch command execution across hosts
│   ├── key_manager.py         # SSH key pair generation (RSA/Ed25519)
│   ├── security.py            # Multi-level security (command/path validation)
│   ├── audit_logger.py        # Structured audit logging
│   ├── logging_config.py      # Centralized logging (SSHLogger singleton)
│   ├── watchdog.py            # Task monitoring & health check
│   ├── exceptions.py         # Custom exception hierarchy
│   └── clients/               # SSH client implementations
│       ├── __init__.py        # Exports: SSHClientInterface, ClientType, etc.
│       ├── interface.py       # Abstract base class + data models
│       ├── factory.py         # Client factory with registration
│       ├── paramiko_client.py # Paramiko implementation
│       └── additional_clients.py  # AsyncSSH/Fabric/SSH2 (optional)
├── config/                     # Runtime configuration
│   ├── hosts.json             # SSH host configurations
│   ├── mcp.user.config.json.example
│   ├── mcp.presets.json
│   └── ssh-hosts.example.json
├── .github/workflows/
│   ├── pypi.yml               # PyPI release workflow
│   └── mcp-registry.yml       # MCP Registry publish workflow
├── openspec/                   # OpenSpec specifications
│   └── specs/                  # Feature specs
├── docs/                       # Documentation
│   ├── API_REFERENCE.md
│   ├── CONTRIBUTING.md
│   └── skills/                # Skill documentation copies
├── pyproject.toml              # Package configuration
├── sync_version.py            # Version sync script
├── Dockerfile                 # Docker image build (multi-stage)
└── .trae/skills/              # Trae IDE skills
```

## Git Workflow

### Always create a new branch for changes

```bash
git checkout master
git pull github master
git checkout -b feature/your-feature-name
```

### Branch Naming Conventions

| Type | Example | Use Case |
|------|---------|----------|
| `feat/` | `feat/add-server-management` | New features |
| `fix/` | `fix/password-display-issue` | Bug fixes |
| `docs/` | `docs/update-readme` | Documentation |
| `refactor/` | `refactor/improve-code` | Code improvements |

### Commit Message Format

```
<type>: <description>
```

Types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`

## Quick Commands

```bash
pip install -e . --user
python -m pytest
python -m build
python -m twine upload dist/* -u __token__ -p <TOKEN>
python -c "from ssh_mcp import __version__; print(__version__)"
```

## Version Management

```bash
python sync_version.py 0.5.6
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

## MCP Tools (17 tools)

| Tool | Description |
|------|-------------|
| `ssh_config` | Configure and save SSH connection settings to local config |
| `ssh_login` | Quick login using pre-saved config or MCP env vars (optionally execute command) |
| `ssh_connect` | Full control connection with explicit params (password/key/agent auth) |
| `ssh_execute` | Execute command on active session (auto-detect background for long-running) |
| `ssh_execute_wait` | Execute command with configurable timeout (5-60s range) |
| `ssh_disconnect` | Close an active SSH session |
| `ssh_list_hosts` | List configured hosts + password conflict detection |
| `ssh_list_sessions` | List all active sessions with connection details |
| `ssh_add_host` | Add new server to hosts.json |
| `ssh_remove_host` | Remove server from hosts.json |
| `ssh_generate_key` | Generate SSH key pair (RSA/Ed25519) |
| `ssh_file_transfer` | Upload/download files via SFTP |
| `ssh_background_task` | Execute long-running commands in background with status polling |
| `ssh_task_status` | Check background task status and progress |
| `ssh_docker_build` | Build Docker image on remote server (background mode) |
| `ssh_docker_status` | Check Docker containers/images/build logs |
| `ssh_container_logs` | Retrieve Docker container logs with tailing |

## Security Features

### Multi-Level Security Strategy

| Level | Env Value | Use Case |
|-------|-----------|----------|
| Strict | `SSH_SECURITY_LEVEL=strict` | Production (whitelist only) |
| Balanced | `SSH_SECURITY_LEVEL=balanced` | Default |
| Relaxed | `SSH_SECURITY_LEVEL=relaxed` | Development/testing |

### Security Components
- **CommandValidator** (`security.py`): Whitelist-based command validation
- **PathValidator** (`security.py`): Path traversal prevention
- **Rate Limiting**: Sliding window algorithm (configurable)
- **Audit Logging**: Structured event logging (connect/disconnect/command/file transfer)

### Security Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SSH_SECURITY_LEVEL` | balanced | Security level (strict/balanced/relaxed) |
| `SSH_EXTRA_ALLOWED_COMMANDS` | - | Additional allowed commands |
| `SSH_EXTRA_ALLOWED_PATTERNS` | - | Additional allowed patterns (e.g. `\|,>,<,&,;`) |
| `SSH_RATE_LIMIT` | true | Enable rate limiting |
| `SSH_RATE_LIMIT_MAX` | 30 | Max requests per window |
| `SSH_RATE_LIMIT_WINDOW` | 60 | Time window in seconds |
| `SSH_AUDIT_LOG_PATH` | - | Audit log file path |

## SSH Client Types

Supported types (via `SSHClientFactory`):
- `paramiko` - Pure Python, stable, registered by default
- `asyncssh` - Async high performance (optional)
- `fabric` - High-level API (optional)
- `ssh2` - C extension (optional)

Default client type in `ConnectionConfig`: `asyncssh`

### Configuration Priority (ssh_connect)

**Default mode** (user params highest):
1. User parameters (args) - Highest
2. hosts.json (by name) - Medium
3. MCP environment variables - Lowest (fallback)

**Force env mode** (`SSH_FORCE_ENV_CONFIG=true`):
1. MCP environment variables - Highest
2. User parameters - Fallback

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
        "SSH_TIMEOUT": "60",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200",
        "SSH_CLIENT_TYPE": "asyncssh",
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_RATE_LIMIT": "true"
      }
    }
  }
}
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `server.py` | MCP server (SSHMCPServer) - tool registration & dispatch |
| `service.py` | SSH service protocol, ClientType enum, HealthCheckResult |
| `session_manager.py` | Session lifecycle (create/close/list), SessionInfo, SessionState |
| `connection_config.py` | Pydantic model with validation (port, timeout, auth) |
| `connection_pool.py` | PooledConnection, PoolConfig, health monitoring |
| `executor.py` | ThreadPoolExecutor singleton, async bridge for blocking ops |
| `batch_executor.py` | BatchExecutionResult, HostResult, parallel execution |
| `security.py` | CommandValidator, PathValidator, SecurityLevel, SecurityError |
| `audit_logger.py` | AuditLogger singleton, AuditEventType enum |
| `watchdog.py` | Watchdog monitor, TaskInfo, WatchdogEvent |
| `key_manager.py` | SSHKeyPair generation (RSA/Ed25519), save/load |
| `logging_config.py` | SSHLogger singleton, file handler support |
| `exceptions.py` | Exception hierarchy (Connection/Auth/Command/File/Session/Timeout/Pool) |
| `clients/interface.py` | SSHClientInterface ABC, ClientType, CommandResult, FileTransferResult |
| `clients/factory.py` | SSHClientFactory, ClientConfig, dynamic registration |
| `clients/paramiko_client.py` | ParamikoClient implementation |

## Docker Configuration

### Build Docker Image

```bash
docker build -t ssh-licco:latest .
docker build -t ssh-licco:0.5.5 .
docker build --build-arg DOCKER_MIRRORS='["https://docker.mirrors.sjtug.sjtu.edu.cn"]' -t ssh-licco:latest .
```

### Run Docker Container

```bash
docker run -d \
  -e SSH_HOST=192.168.1.100 \
  -e SSH_USER=root \
  -e SSH_PASSWORD=your_password \
  -e SSH_SECURITY_LEVEL=balanced \
  ssh-licco:latest
```

### Multi-stage Build
1. **Builder stage**: Install dependencies in venv
2. **Runtime stage**: Minimal runtime (~150MB)

## Common Issues

### Password Special Characters
Passwords with special characters work fine in JSON - no escaping needed.

### SSH Connection Failed
- Check server SSH service: `sudo systemctl status sshd`
- Restart if needed: `sudo systemctl restart sshd`

### Version Not Updated
- Restart Trae IDE after updating
- Or restart MCP server process

### Command Blocked by Security
- Check `SSH_SECURITY_LEVEL` env var
- Add allowed commands via `SSH_EXTRA_ALLOWED_COMMANDS`
- Or temporarily set `SSH_SECURITY_LEVEL=relaxed`

### Rate Limit Triggered
- Check `SSH_RATE_LIMIT_MAX` and `SSH_RATE_LIMIT_WINDOW`
- Disable temporarily: `SSH_RATE_LIMIT=false`

## Development Workflow (Complete)

1. **Create branch** from master
2. **Make changes** to source code in `ssh_mcp/`
3. **Test locally**: `pip install -e . --user`
4. **Commit and push**: `git push -u github feat/your-feature`
5. **Create Pull Request** on GitHub
6. **After PR merged**: Update version, build, upload to PyPI
7. **Update local master**: `git pull github master`

## Key Files Reference

| File | Purpose |
|------|---------|
| `ssh_mcp/__init__.py` | Version (main) |
| `ssh_mcp/server.py` | MCP server logic + all tool handlers |
| `ssh_mcp/security.py` | Security validation (command/path) |
| `ssh_mcp/audit_logger.py` | Audit logging |
| `ssh_mcp/connection_config.py` | Connection config Pydantic model |
| `ssh_mcp/session_manager.py` | Session management |
| `ssh_mcp/service.py` | Service protocol & health check |
| `ssh_mcp/exceptions.py` | Exception hierarchy |
| `config/hosts.json` | Saved SSH hosts |
| `pyproject.toml` | Package config |
| `Dockerfile` | Docker image build |
| `sync_version.py` | Version sync script |

## Documentation Reference

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `USAGE.md` | Detailed usage guide |
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
