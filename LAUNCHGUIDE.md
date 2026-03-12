# ssh-licco MCP Server

## Description
SSH Model Context Protocol Server - Enable SSH functionality for AI models. Connect to SSH servers and execute commands via AI assistants.

## Features
- 🎯 Natural language control - Control servers through conversation
- 🔐 Multiple authentication methods - Password, key, agent forwarding
- 🔗 Long connection support - Auto keepalive (30s), avoid account lockout
- ⏱️ Configurable timeout - Banner timeout (60s), session timeout (2 hours)
- 📦 Asynchronous high performance - Based on AsyncSSH
- 🛡️ Complete error handling - Unified error handling mechanism
- 📊 Session management - Support multiple concurrent SSH sessions
- 📁 SFTP file transfer - Upload, download, directory management
- 🔑 Key management - Generate and manage SSH key pairs
- 📝 Audit logging - Complete operation audit records
- 🚀 Connection pool - High-performance connection reuse
- 📊 Batch execution - Multi-host parallel command execution
- 🐳 Docker support - Docker build and status monitoring
- 📋 Background tasks - Asynchronous task execution and status tracking

## Installation

### Via PyPI
```bash
pip install ssh-licco
```

### Via MCP CLI
```bash
mcp install io.github.Echoqili/ssh-licco
```

## Configuration

### Basic Configuration
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

### With Environment Variables
```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco",
      "env": {
        "SSH_HOST": "192.168.1.100",
        "SSH_USER": "root",
        "SSH_PASSWORD": "your_password",
        "SSH_PORT": "22"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| SSH_HOST | SSH server hostname | No | - |
| SSH_USER | SSH username | No | root |
| SSH_PASSWORD | SSH password | No | - |
| SSH_PORT | SSH port | No | 22 |
| SSH_TIMEOUT | Connection timeout (seconds) | No | 120 |
| SSH_KEEPALIVE_INTERVAL | Keepalive interval (seconds) | No | 30 |
| SSH_SESSION_TIMEOUT | Session timeout (seconds) | No | 7200 |

## Available Tools

- `ssh_config` - Configure SSH connection
- `ssh_login` - Login using saved config
- `ssh_connect` - Direct SSH connection
- `ssh_execute` - Execute commands
- `ssh_disconnect` - Disconnect session
- `ssh_list_sessions` - List active sessions
- `ssh_file_transfer` - SFTP file transfer
- `ssh_generate_key` - Generate SSH keys
- `ssh_background_task` - Create background tasks
- `ssh_task_status` - Check task status
- `ssh_docker_build` - Docker image build
- `ssh_docker_status` - Docker status check

## Usage Examples

### Execute Command
```
Help me check the server load
```

### View Running Processes
```
Execute `docker ps` on the server to see running containers
```

### Manage Files
```
List all files in /var/log directory
```

### Upload File
```
Upload config.yaml to /etc directory on server
```

## Security

⚠️ **Important Security Notes**:

1. **Password Security** - Passwords stored locally only
2. **Don't Share** - Never share server credentials publicly
3. **Key Authentication** - Prefer SSH key authentication
4. **Regular Users** - Use regular user accounts, not root when possible
5. **File Permissions** - Ensure config files have 600 permissions
6. **Environment Variables** - Use env vars for sensitive information

## Links

- **GitHub**: https://github.com/Echoqili/ssh-licco
- **PyPI**: https://pypi.org/project/ssh-licco/
- **MCP Registry**: https://registry.modelcontextprotocol.io/servers/io.github.Echoqili/ssh-licco

## License

MIT License

## Author

SSH LICCO Team
