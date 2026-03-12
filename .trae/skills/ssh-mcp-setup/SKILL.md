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
# Clone repository
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco

# Install in development mode
pip install -e . --user
```

### Update Version
```bash
pip install --upgrade ssh-licco
```

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
        "SSH_TIMEOUT": "120",
        "SSH_KEEPALIVE_INTERVAL": "30",
        "SSH_SESSION_TIMEOUT": "7200"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| SSH_HOST | 127.0.0.1 | SSH server hostname |
| SSH_PORT | 22 | SSH server port |
| SSH_USER | root | SSH username |
| SSH_PASSWORD | - | SSH password |
| SSH_TIMEOUT | 30 | Connection timeout (seconds) |
| SSH_KEEPALIVE_INTERVAL | 30 | Keepalive interval (seconds) |
| SSH_SESSION_TIMEOUT | 7200 | Session timeout (seconds) |
| SSH_CLIENT_TYPE | paramiko | SSH client (paramiko/asyncssh) |

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

### client_config.json
Location: `config/client_config.json`

```json
{
  "default_timeout": 30,
  "max_retries": 3,
  "keepalive_interval": 30,
  "session_timeout": 7200,
  "client_type": "paramiko"
}
```

## Configuration Priority

The system reads config in this order (later overrides earlier):

1. **MCP Config** (mcp.json env) - Highest priority
2. **hosts.json** (config/hosts.json)
3. **Tool parameters** (when calling tools)

Example:
```json
// MCP config has SSH_HOST=192.168.1.100
// But tool call specifies host=10.0.0.1

// Result: Uses 10.0.0.1 (tool parameter)
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
# Method 1: ssh-copy-id
ssh-copy-id user@server

# Method 2: Manual
cat ~/.ssh/id_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
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

## Development Setup

### Local Development
```bash
# Install in editable mode
pip install -e . --user

# Test installation
ssh-licco --help

# Or run directly
python -m ssh_mcp.server
```

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Debug Mode
```bash
# Enable verbose logging
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
2. Check PATH: `which ssh-licco`
3. Reinstall: `pip install --upgrade ssh-licco`

### Version Not Updating
1. Restart Trae IDE
2. Kill old MCP process: `Get-Process | Where-Object {$_.Name -like "*ssh-licco*"}`
3. Reinstall: `pip install --force-reinstall --no-deps ssh-licco`

## Project Structure

```
ssh-mcp/
├── ssh_mcp/           # Source code
│   ├── __init__.py   # Version info
│   ├── server.py     # MCP server
│   ├── config_manager.py
│   ├── session_manager.py
│   └── clients/      # SSH clients
├── config/           # Runtime config
│   ├── hosts.json
│   └── client_config.json
├── pyproject.toml    # Package config
└── README.md         # Documentation
```

## Uninstall

```bash
pip uninstall ssh-licco
```

## Get Version

```bash
# Via pip
pip show ssh-licco

# Via Python
python -c "from ssh_mcp import __version__; print(__version__)"
```

## Quick Test

```python
# Test connection
from ssh_mcp import SSHMCPServer

server = SSHMCPServer()
print(f"Version: {server.server.name}")
```
