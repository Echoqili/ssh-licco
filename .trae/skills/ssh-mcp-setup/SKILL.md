---
name: "ssh-mcp-setup"
description: "Local setup and configuration guide for SSH MCP. Invoke when user needs to set up, configure, or customize the SSH MCP server locally."
---

# Local Setup and Configuration Guide

## Installation

### Method 1: npx One-Click (Recommended, Zero Config)

```bash
npx ssh-licco
```

First run automatically: detect Python → create venv → install dependencies → verify integrity → start MCP server. **No manual setup needed.**

This creates an isolated Python venv at `~/.ssh-licco-venv` and avoids all conflicts.

### Method 2: From npm (Recommended for Windows)

```bash
npm install -g ssh-licco
```

Post-install script (`install.js`) auto-detects existing venv and performs incremental update.

### Method 3: From PyPI

```bash
pip install ssh-licco
```

### Method 4: From Source

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e .
```

### Update Version

```bash
# npm
npm update -g ssh-licco

# pip
pip install --upgrade ssh-licco
```

## Auto-Install System Architecture

ssh-licco uses a **three-layer architecture** for zero-config startup:

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

### Smart Install Features

| Feature | Description |
|---------|-------------|
| **Anaconda Auto-Detect** | Detects conda environment, uses isolated venv to avoid conflicts |
| **Dependency Integrity Check** | Verifies all dependencies on every startup, auto-repairs if missing |
| **Incremental Update** | Doesn't delete existing venv, uses `pip install -e .` for incremental install |
| **Auto-Repair** | Auto re-installs when dependencies are corrupted, no manual intervention |

### Key Files

| File | Purpose |
|------|---------|
| `ssh-licco.js` | Node.js wrapper - environment prep, integrity check, startup |
| `install.js` | npm postinstall script - incremental install |
| `smart_install.py` | Standalone diagnostic install script |
| `cli.py` | Python entry point - only starts the MCP server |

## Requirements

- **Python**: >=3.10, <3.14
- **Core dependencies**: mcp>=1.0.0, asyncssh>=2.17.0, paramiko>=2.0.0, pydantic>=2.0.0, pydantic-settings>=2.0.0
- **Key management**: cryptography (for SSH key generation)

## Trae IDE MCP Configuration

### Stable Configuration Pattern (Recommended)

The most stable approach is to use the **isolated venv** directly, bypassing Node.js wrapper and Anaconda:

```json
{
  "mcpServers": {
    "ssh-licco": {
      "command": "C:\\Users\\<YourName>\\.ssh-licco-venv\\Scripts\\ssh-licco.exe",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_PORT": "22",
        "SSH_TIMEOUT": "60",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200",
        "SSH_SECURITY_LEVEL": "balanced",
        "SSH_EXTRA_ALLOWED_COMMANDS": "git,pip,npm,docker,sh"
      }
    }
  }
}
```

**Why this pattern is stable:**
- `~/.ssh-licco-venv` is an **isolated Python environment** created by the auto-installer
- It is **completely independent** of Anaconda, system Python, or npm
- No Node.js wrapper layer means **no shell command parsing issues** on Windows
- Editor directly communicates with the Python MCP server via stdio

Linux/macOS equivalent:
```json
{
  "command": "/home/<user>/.ssh-licco-venv/bin/ssh-licco"
}
```

### Method 1: Via Settings UI
1. Open Trae IDE Settings
2. Search for "MCP"
3. Add SSH MCP server
4. Configure command: `C:\Users\<YourName>\.ssh-licco-venv\Scripts\ssh-licco.exe`
5. Add environment variables

### Method 2: Via JSON Config

Find MCP config file location:
- **Trae IDE**: `C:\Users\<YourName>\AppData\Roaming\Trae\User\mcp.json`

### How MCP Environment Affects Stability

MCP (Model Context Protocol) uses **stdio** (stdin/stdout) for JSON-RPC communication. The editor and MCP server exchange JSON messages over these pipes. This means:

1. **Any non-JSON output to stdout breaks the protocol** — install logs, warnings, progress bars all corrupt the MCP handshake
2. **stderr is safe** — it's a separate pipe for server logs
3. **Startup must be fast** — if the server takes too long to start, the editor times out and abandons the connection

**Common failure patterns and solutions:**

| Problem | Cause | Solution |
|---------|-------|----------|
| Tools not showing | Server output to stdout corrupted protocol | Use venv directly (no wrapper) |
| `ModuleNotFoundError` | Anaconda package corrupted | Clean `~` prefix dirs, reinstall to venv |
| Timeout on startup | Wrapper doing pip install on every start | Fix integrity check (don't use `shell: true` on Windows) |
| `Cannot find module` | Damaged npm global package | Run `npm uninstall -g ssh-licco` |

## Environment Variables

### Connection Settings

| Variable | Default | Description |
|----------|---------|-------------|
| SSH_HOST | 127.0.0.1 | SSH server hostname |
| SSH_PORT | 22 | SSH server port |
| SSH_USER | root | SSH username |
| SSH_PASSWORD | - | SSH password |
| SSH_TIMEOUT | 60 | Connection timeout (seconds) |
| SSH_KEEPALIVE_INTERVAL | 30 | Keepalive interval (seconds) |
| SSH_SESSION_TIMEOUT | 7200 | Session timeout (seconds) |
| SSH_CLIENT_TYPE | asyncssh | SSH client (paramiko/asyncssh) |
| SSH_FORCE_ENV_CONFIG | false | Force env vars as highest priority |
| SSH_LICCO_AUTO_INSTALL | true | Enable/disable auto-install on first run |

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| SSH_SECURITY_LEVEL | balanced | Security level (strict/balanced/relaxed) |
| SSH_EXTRA_ALLOWED_COMMANDS | - | Additional allowed commands (comma-separated) |
| SSH_RATE_LIMIT | true | Enable rate limiting (bool: true/false) |
| SSH_RATE_LIMIT_MAX | 30 | Max requests per window |
| SSH_RATE_LIMIT_WINDOW | 60 | Time window in seconds |
| SSH_AUDIT_LOG_PATH | - | Audit log file path |

## Local Configuration Files

### hosts.json
Location: `config/hosts.json`

```json
{
  "ssh_hosts": [
    {
      "name": "production",
      "host": "43.143.207.242",
      "port": 22,
      "username": "root",
      "password": "",
      "timeout": 120,
      "keepalive_interval": 30,
      "session_timeout": 7200
    },
    {
      "name": "development",
      "host": "192.168.1.100",
      "port": 22,
      "username": "ubuntu",
      "password": "",
      "timeout": 60
    }
  ]
}
```

## Configuration Priority

### Default Mode (user params highest)

1. **User parameters** (when calling tools) - Highest
2. **hosts.json** (config/hosts.json by name) - Medium
3. **MCP Config** (mcp.json env) - Lowest (fallback)

### Force Env Mode (`SSH_FORCE_ENV_CONFIG=true`)

1. **MCP Config** (mcp.json env) - Highest
2. **User parameters** - Fallback

Example:
```
MCP config has SSH_HOST=192.168.1.100
But tool call specifies host=10.0.0.1

Default mode: Uses 10.0.0.1 (user parameter)
Force env mode: Uses 192.168.1.100 (env config)
```

## Password Security

### Best Practices
1. Use environment variables for passwords
2. Don't commit passwords to Git
3. Use SSH keys when possible
4. Rotate passwords regularly

### Password with Special Characters
Passwords with special characters work fine in JSON:
```json
{
  "SSH_PASSWORD": "P/[KY}+wa7?2|uc"
}
```
No escaping needed!

## Using SSH Keys

### Generate Key
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### Add to Server
```bash
ssh-copy-id user@server
```

### Configure MCP to Use Key
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "ubuntu",
        "SSH_PRIVATE_KEY_PATH": "/path/to/private/key",
        "SSH_PASSPHRASE": "your_passphrase"
      }
    }
  }
}
```

### Connect with Key via Tool
```
连接 SSH，host=xxx, username=ubuntu, private_key_path=/path/to/key, auth_method=private_key
```

## Security Configuration

### Security Levels

| Level | Use Case | Description |
|-------|----------|-------------|
| strict | Production | Only whitelisted commands, strict path validation |
| balanced | Default | Most commands allowed, dangerous patterns blocked |
| relaxed | Development | Permissive, minimal restrictions |

### Example: Strict Mode for Production
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "prod-server",
        "SSH_SECURITY_LEVEL": "strict",
        "SSH_RATE_LIMIT": "true",
        "SSH_RATE_LIMIT_MAX": "10",
        "SSH_AUDIT_LOG_PATH": "/var/log/ssh-mcp-audit.json"
      }
    }
  }
}
```

### Example: Relaxed Mode for Development
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "dev-server",
        "SSH_SECURITY_LEVEL": "relaxed",
        "SSH_RATE_LIMIT": "false"
      }
    }
  }
}
```

## Development Setup

### Local Development
```bash
pip install -e .
ssh-licco --help
python -m ssh_mcp.server
```

### Run Tests
```bash
pip install pytest pytest-asyncio pytest-cov
pytest
```

### Lint & Type Check
```bash
ruff check ssh_mcp/
mypy ssh_mcp/
```

### Debug Mode
```bash
export DEBUG=1
ssh-licco
```

## Troubleshooting Setup

### MCP Not Loading
1. Check MCP config file exists
2. Validate JSON syntax
3. Restart Trae IDE

### Command Not Found
1. Check pip installation: `pip show ssh-licco`
2. Check PATH: `where ssh-licco` (Windows) or `which ssh-licco` (Linux)
3. Reinstall: `pip install --upgrade ssh-licco`

### npx Cannot Find Module Error

**Cause**: Damaged npm global package

**Fix**:
```bash
npm uninstall -g ssh-licco
# Then retry npx ssh-licco
```

### Dependency Incomplete

ssh-licco auto-verifies dependencies on every startup and auto-repairs if missing. You can also run manually:

```bash
node install.js
```

### Version Not Updating
1. Restart Trae IDE
2. Kill old MCP process: `Get-Process | Where-Object {$_.Name -like "*ssh-licco*"}`
3. Reinstall: `pip install --force-reinstall --no-deps ssh-licco`

### Commands Blocked by Security
1. Check `SSH_SECURITY_LEVEL` setting
2. Add specific allowed commands: `SSH_EXTRA_ALLOWED_COMMANDS`
3. Temporarily use relaxed mode for testing

## Project Structure

```
ssh-mcp/
├── ssh_mcp/           # Source code
│   ├── __init__.py   # Version info
│   ├── server.py     # MCP server (17 tools)
│   ├── security.py   # Multi-level security
│   ├── audit_logger.py # Audit logging
│   ├── connection_config.py # Pydantic config model
│   ├── session_manager.py  # Session management
│   ├── service.py    # Service protocol
│   ├── connection_pool.py  # Connection pooling
│   ├── executor.py   # Thread pool executor
│   ├── batch_executor.py   # Batch execution
│   ├── key_manager.py # SSH key management
│   ├── watchdog.py   # Health monitoring
│   ├── logging_config.py # Centralized logging
│   ├── exceptions.py # Exception hierarchy
│   └── clients/      # SSH clients (paramiko/asyncssh/fabric/ssh2)
├── ssh-licco.js      # Node.js wrapper (auto-install + startup)
├── install.js        # npm postinstall script
├── smart_install.py  # Standalone diagnostic installer
├── config/           # Runtime config
│   ├── hosts.json
│   └── mcp.presets.json
├── pyproject.toml    # Package config
└── README.md         # Documentation
```

## Uninstall

```bash
# pip installed
pip uninstall ssh-licco

# npm installed
npm uninstall -g ssh-licco

# Clean up venv if needed
rm -rf ~/.ssh-licco-venv
```

## Get Version

```bash
pip show ssh-licco
python -c "from ssh_mcp import __version__; print(__version__)"
```