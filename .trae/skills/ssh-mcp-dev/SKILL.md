---
name: "ssh-mcp-dev"
description: "SSH MCP server development guide. Invoke when working on ssh-licco project, including setup, debugging, version management, Docker deployment, and releases."
---

# SSH MCP Server Development Guide

## Project Overview

- **Project Name**: ssh-licco
- **Description**: SSH Model Context Protocol Server - Enable SSH functionality for AI models
- **Repository**: https://github.com/Echoqili/ssh-licco
- **Current Version**: 1.9.5 (stored in `ssh_mcp/__init__.py`)
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
│   ├── cli.py                # Python entry point (simplified to only start server)
│   └── clients/               # SSH client implementations
│       ├── __init__.py        # Exports: SSHClientInterface, ClientType, etc.
│       ├── interface.py       # Abstract base class + data models
│       ├── factory.py         # Client factory with registration
│       ├── paramiko_client.py # Paramiko implementation
│       └── additional_clients.py  # AsyncSSH/Fabric/SSH2 (optional)
├── ssh-licco.js              # Node.js wrapper - auto-install + integrity check + startup
├── install.js                # npm postinstall script - incremental install
├── smart_install.py          # Standalone diagnostic installer with SSH test
├── config/                    # Runtime configuration
│   ├── hosts.json            # SSH host configurations
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
├── sync_version.py            # Version sync script (syncs all version files)
└── .trae/skills/              # Trae IDE skills
```

## Auto-Install System Architecture

The npx auto-install uses a **three-layer architecture**:

```
User → npx ssh-licco
           ↓
    ┌──── ssh-licco.js (Node Layer) ────┐
    │  ① Find Python 3.10+             │
    │  ② Detect Anaconda environment   │
    │  ③ Create/reuse ~/.ssh-licco-venv │
    │  ④ pip install dependencies      │
    │  ⑤ Verify dependency integrity   │
    └──────────┬────────────────────────┘
               ↓
    ┌── cli.py (Python Entry) ──────┐
    │  Only starts MCP server       │
    └──────────┬────────────────────┘
               ↓
    ┌── SSHMCPServer (MCP Service) ─┐
    │  SSH connect, execute, etc.   │
    └───────────────────────────────┘
```

### Key Design Decisions

1. **Node.js wrapper (`ssh-licco.js`) handles all environment prep** - Python finding, venv creation, dependency installation, integrity verification. This ensures the Python layer can focus purely on MCP logic.

2. **Incremental install (`install.js`)** - The postinstall script checks `venvHasInstallation()` first. If the venv already has valid dependencies, it skips deletion and does incremental `pip install -e .`. This makes re-installs nearly instant.

3. **cli.py is stripped down** - No duplicate install logic. Only 17 lines: imports `run_server()` and calls it.

4. **Dependency integrity check** - Every startup verifies `from ssh_mcp.server import SSHMCPServer; from ssh_mcp.session_manager import SessionManager` works. If not, auto-repairs.

5. **Anaconda detection** - Both `ssh-licco.js` and `install.js` detect Anaconda/Miniconda Python and log a warning, ensuring users know their conda environment won't be touched.

### Smart Install Features

| Feature | Description |
|---------|-------------|
| **Anaconda Auto-Detect** | Detects conda environment, uses isolated venv |
| **Dependency Integrity Check** | Verifies on startup, auto-repairs if missing |
| **Incremental Update** | Doesn't delete venv, `pip install -e .` only |
| **Auto-Repair** | Re-installs when deps corrupted |

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
pip install -e .
python -m pytest
python -m build
python -m twine upload dist/* -u __token__ -p <TOKEN>
python -c "from ssh_mcp import __version__; print(__version__)"
```

## Version Management

```bash
python sync_version.py x.x.x
```

### Version Files (sync automatically)
- `ssh_mcp/__init__.py` - Main version file (source of truth)
- `pyproject.toml` - PyPI package version
- `VERSION` - Plain text backup
- `package.json` - npm package version

### Release Process
1. Update version: `python sync_version.py x.x.x` (syncs ALL files at once)
2. Build: `python -m build`
3. Upload: `python -m twine upload dist/*`
4. Create GitHub Release: `git tag vx.x.x && git push origin vx.x.x`

### Version Files Reference
| File | Synced By sync_version.py |
|------|---------------------------|
| `ssh_mcp/__init__.py` | Yes (__version__ + version comment) |
| `pyproject.toml` | Yes (version field) |
| `VERSION` | Yes (plain text) |
| `package.json` | Yes (version field) |

## MCP Tools (7 tools, consolidated from 17)

| Tool | Description |
|------|-------------|
| `ssh_connect` | Connect to SSH server (auto-reads env vars, saved config, or explicit params). Supports password/key/agent auth, optional save_config, and optional post-connect command. |
| `ssh_execute` | Execute commands on remote server. Auto-connects if no session_id. Auto-detects background execution for long-running tasks. Supports `background`, `wait`, `workdir`, `log_file`, `wait_timeout` params. |
| `ssh_disconnect` | Close a session (with session_id) or list all active sessions (without session_id). |
| `ssh_file_transfer` | Upload/download/list files via SFTP. |
| `ssh_host` | Manage server configs: `action=list` (view all), `action=add` (register new), `action=remove` (delete). |
| `ssh_docker` | Docker management: `action=ps` (list containers), `action=images` (list images), `action=build` (build image in background), `action=logs` (view container logs). |
| `ssh_generate_key` | Generate SSH key pair (RSA/Ed25519). |

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
| `ssh-licco.js` | Node.js wrapper - auto-install, Anaconda detection, integrity check |
| `install.js` | npm postinstall - incremental venv install |
| `cli.py` | Python entry - simplified startup only |
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

### npx Cannot Find Module Error
- Cause: Damaged npm global package
- Fix: `npm uninstall -g ssh-licco`

### Dependency Missing
- ssh-licco auto-verifies and repairs on startup
- Manual: `node install.js`

## Development Workflow (Complete)

1. **Create branch** from master
2. **Make changes** to source code in `ssh_mcp/` or wrapper files (`ssh-licco.js`, `install.js`)
3. **Test locally**: `pip install -e .`
4. **Commit and push**: `git push -u github feat/your-feature`
5. **Create Pull Request** on GitHub
6. **After PR merged**: Update version, build, upload to PyPI
7. **Update local master**: `git pull github master`

## Key Files Reference

| File | Purpose |
|------|---------|
| `ssh-licco.js` | Node.js auto-install wrapper |
| `install.js` | npm postinstall script |
| `ssh_mcp/__init__.py` | Version (main) |
| `ssh_mcp/server.py` | MCP server logic + all tool handlers |
| `ssh_mcp/security.py` | Security validation (command/path) |
| `ssh_mcp/audit_logger.py` | Audit logging |
| `ssh_mcp/connection_config.py` | Connection config Pydantic model |
| `ssh_mcp/session_manager.py` | Session management |
| `ssh_mcp/service.py` | Service protocol & health check |
| `ssh_mcp/exceptions.py` | Exception hierarchy |
| `ssh_mcp/cli.py` | Python entry point |
| `config/hosts.json` | Saved SSH hosts |
| `pyproject.toml` | Package config |
| `sync_version.py` | Version sync script (syncs all version files) |

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