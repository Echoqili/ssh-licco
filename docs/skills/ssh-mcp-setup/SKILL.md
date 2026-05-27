---
name: "ssh-mcp-setup"
description: "Local setup and configuration guide for SSH MCP. Invoke when user needs to set up, configure, or customize the SSH MCP server locally."
---

# Local Setup and Configuration Guide

## Installation

### From PyPI (Recommended)
```bash
pip install ssh-licco
```

### From Source
```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e . --user
```

### Update Version
```bash
pip install --upgrade ssh-licco
```

## Requirements

- **Python**: >=3.10, <3.14
- **Core dependencies**: mcp>=1.0.0, asyncssh>=2.17.0, pydantic>=2.0.0, pydantic-settings>=2.0.0
- **Key management**: cryptography (for SSH key generation)
- **Optional**: paramiko (alternative SSH client)

## Trae IDE MCP Configuration

### Method 1: Via Settings UI
1. Open Trae IDE Settings
2. Search for "MCP"
3. Add SSH MCP server
4. Configure command: `ssh-licco`
5. Add environment variables

### Method 2: Via JSON Config

Find MCP config file location:
- **Trae IDE**: `C:\Users\<YourName>\AppData\Roaming\Trae\User\mcp.json`

Add configuration:
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

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| SSH_SECURITY_LEVEL | balanced | Security level (strict/balanced/relaxed) |
| SSH_EXTRA_ALLOWED_COMMANDS | - | Additional allowed commands (comma-separated) |
| SSH_EXTRA_ALLOWED_PATTERNS | - | Additional allowed patterns (e.g. `\|,>,<,&,;`) |
| SSH_RATE_LIMIT | true | Enable rate limiting |
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
        "SSH_RATE_LIMIT": "false",
        "SSH_EXTRA_ALLOWED_PATTERNS": "|,>,<,&,;"
      }
    }
  }
}
```

## Development Setup

### Local Development
```bash
pip install -e . --user
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

### Version Not Updating
1. Restart Trae IDE
2. Kill old MCP process: `Get-Process | Where-Object {$_.Name -like "*ssh-licco*"}`
3. Reinstall: `pip install --force-reinstall --no-deps ssh-licco`

### Commands Blocked by Security
1. Check `SSH_SECURITY_LEVEL` setting
2. Add specific allowed commands: `SSH_EXTRA_ALLOWED_COMMANDS`
3. Add allowed patterns: `SSH_EXTRA_ALLOWED_PATTERNS`
4. Temporarily use relaxed mode for testing

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
├── config/           # Runtime config
│   ├── hosts.json
│   └── mcp.presets.json
├── pyproject.toml    # Package config
└── README.md         # Documentation
```

## Uninstall

```bash
pip uninstall ssh-licco
```

## Get Version

```bash
pip show ssh-licco
python -c "from ssh_mcp import __version__; print(__version__)"
```