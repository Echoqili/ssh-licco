"""MCP tool schema definitions."""

from __future__ import annotations

from mcp.types import Tool


TOOLS: dict[str, Tool] = {
    "ssh_connect": Tool(
        name="ssh_connect",
        description="Establish an SSH connection to a remote server. If no parameters are provided, auto-connects using environment variables or saved config. Supports password, private key, and agent authentication. Optionally save the config and/or execute a command after connecting.",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "SSH server hostname or IP. If omitted, auto-reads from env vars or saved config."},
                "port": {"type": "integer", "description": "SSH port", "default": 22},
                "username": {"type": "string", "description": "SSH username. If omitted, auto-reads from env vars."},
                "password": {"type": "string", "description": "SSH password for password-based auth."},
                "private_key_path": {"type": "string", "description": "Path to private key file for key-based auth."},
                "passphrase": {"type": "string", "description": "Passphrase for encrypted private key."},
                "auth_method": {"type": "string", "enum": ["password", "private_key", "agent"], "default": "private_key", "description": "Authentication method."},
                "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name."},
                "save_config": {"type": "boolean", "description": "Save connection settings to local config file for future use.", "default": False},
                "command": {"type": "string", "description": "Optional command to execute immediately after connecting."},
                "accept_new_host_key": {"type": "boolean", "default": True, "description": "Auto-accept new host keys."},
                "sudo_password": {"type": "string", "description": "Sudo password (optional). When set, ssh_execute with use_sudo=true will auto-wrap commands with sudo -S, avoiding plaintext password in process list."}
            }
        }
    ),
    "ssh_execute": Tool(
        name="ssh_execute",
        description="Execute a command on a remote server. If session_id is omitted, auto-connects using environment variables. Supports background execution for long-running tasks (auto-detected or manual). Use session_type='screen' or 'tmux' for persistent sessions that survive SSH disconnect.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID from ssh_connect. If omitted, connects via name/host/env vars."},
                "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name. Alternative to session_id."},
                "host": {"type": "string", "description": "SSH server hostname or IP. Alternative to session_id/name, can override hosts.json entry."},
                "port": {"type": "integer", "description": "SSH port (used with host).", "default": 22},
                "username": {"type": "string", "description": "SSH username (used with host)."},
                "password": {"type": "string", "description": "SSH password (used with host)."},
                "command": {"type": "string", "description": "Shell command to execute on the remote server (required)."},
                "timeout": {"type": "integer", "description": "Command timeout in seconds. Default 120s. For long tasks (docker pull, pg_basebackup), set higher or use background=true.", "default": 120},
                "background": {"type": "boolean", "description": "Run in background for long-running tasks. Auto-detected if not specified."},
                "workdir": {"type": "string", "description": "Working directory for background tasks.", "default": "/tmp"},
                "log_file": {"type": "string", "description": "Log file path for background task output.", "default": "/tmp/background_task.log"},
                "wait": {"type": "boolean", "description": "Wait for background task to complete.", "default": False},
                "wait_timeout": {"type": "integer", "description": "Max wait time in seconds when wait=True.", "default": 60},
                "session_type": {"type": "string", "enum": ["nohup", "screen", "tmux"], "default": "nohup", "description": "Background session type: nohup (default), screen, or tmux (persistent)."},
                "use_sudo": {"type": "boolean", "default": False, "description": "Wrap command with sudo -S using sudo_password from ssh_connect. Password is passed via stdin, not visible in process list."},
                "confirm_dangerous": {"type": "boolean", "default": False, "description": "Bypass security validation for known-dangerous commands (e.g. rm -rf /path). Use with caution — only for operations you explicitly intend to perform."},
                "approval_id": {"type": "string", "description": "加固点 4：高危操作审批 ID。当 SSH_APPROVAL_GATE=true 且命令被判定为高危时，必须先调用 ssh_request_approval 获取 approval_id，再带上此参数执行。否则高危命令会被拒绝。"},
                "remote_guard": {"type": "boolean", "default": False, "description": "加固点 3：标记远端已启用 ForceCommand 二次校验。启用后 ssh-licco 侧会强制把命令规范为单一 argv 形式下发，禁止 shell 元字符，确保远端 bash -c 解析时无法绕过白名单。"}
            },
            "required": ["command"]
        }
    ),
    "ssh_disconnect": Tool(
        name="ssh_disconnect",
        description="Close an active SSH session. If no session_id is provided, lists all currently active sessions with connection details.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to disconnect. If omitted, lists all active sessions."}
            }
        }
    ),
    "ssh_file_transfer": Tool(
        name="ssh_file_transfer",
        description="Transfer and manage files between local and remote server via SFTP. Supports upload, download, list, write (write content directly to remote file), append, delete, mkdir, stat, and remote_copy (server-to-server direct transfer via scp/rsync, avoiding local relay).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active SSH session ID. If omitted, connects via name/host/env vars."},
                "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name. Alternative to session_id."},
                "host": {"type": "string", "description": "SSH server hostname or IP. Alternative to session_id/name, can override hosts.json entry."},
                "port": {"type": "integer", "description": "SSH port (used with host).", "default": 22},
                "username": {"type": "string", "description": "SSH username (used with host)."},
                "password": {"type": "string", "description": "SSH password (used with host)."},
                "direction": {"type": "string", "enum": ["upload", "download", "list", "write", "append", "delete", "mkdir", "stat", "remote_copy"], "description": "Action: upload, download, list, write (content->remote file), append, delete, mkdir, stat, remote_copy (server-to-server direct transfer)."},
                "local_path": {"type": "string", "description": "Local file path. Required for upload/download."},
                "remote_path": {"type": "string", "description": "Remote file/directory path. Required for all directions. For remote_copy, this is the source path on the connected server."},
                "content": {"type": "string", "description": "Content to write/append to remote file. Required for write/append."},
                "target_host": {"type": "string", "description": "remote_copy: Target server hostname/IP."},
                "target_port": {"type": "integer", "description": "remote_copy: Target SSH port.", "default": 22},
                "target_user": {"type": "string", "description": "remote_copy: Target SSH username.", "default": "root"},
                "target_path": {"type": "string", "description": "remote_copy: Destination path on target server."},
                "target_password": {"type": "string", "description": "remote_copy: Target server password (uses sshpass). If omitted, assumes key-based auth is configured."},
                "use_rsync": {"type": "boolean", "default": False, "description": "remote_copy: Use rsync instead of scp (better for large directories, supports resume)."}
            },
            "required": ["session_id", "direction"]
        }
    ),
    "ssh_host": Tool(
        name="ssh_host",
        description="Manage SSH server configurations in hosts.json. Use action=list to view all hosts, action=add to register a new server, action=remove to delete a server.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "add", "remove"], "description": "Action: list all hosts, add a new host, or remove a host."},
                "name": {"type": "string", "description": "Friendly name for the server. Required for add and remove."},
                "host": {"type": "string", "description": "Server hostname or IP. Required for add."},
                "port": {"type": "integer", "description": "SSH port number.", "default": 22},
                "username": {"type": "string", "description": "SSH login username.", "default": "root"},
                "password": {"type": "string", "description": "SSH password (optional for key auth)."},
                "timeout": {"type": "integer", "description": "Connection timeout in seconds.", "default": 60}
            },
            "required": ["action"]
        }
    ),
    "ssh_docker": Tool(
        name="ssh_docker",
        description="Manage Docker on the remote server. Supports ps (list containers), images (list images), build (build an image in background), and logs (view container logs).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active SSH session ID. If omitted, connects via name/host/env vars."},
                "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name. Alternative to session_id."},
                "host": {"type": "string", "description": "SSH server hostname or IP. Alternative to session_id/name, can override hosts.json entry."},
                "port": {"type": "integer", "description": "SSH port (used with host).", "default": 22},
                "username": {"type": "string", "description": "SSH username (used with host)."},
                "password": {"type": "string", "description": "SSH password (used with host)."},
                "action": {"type": "string", "enum": ["ps", "images", "build", "logs"], "description": "Docker action: ps=list containers, images=list images, build=build an image, logs=view container logs."},
                "image_name": {"type": "string", "description": "Docker image name. Required for build, optional filter for images."},
                "container_name": {"type": "string", "description": "Container name or ID. Required for logs."},
                "dockerfile_path": {"type": "string", "description": "Path to Dockerfile for build.", "default": "./Dockerfile"},
                "context": {"type": "string", "description": "Build context directory for build.", "default": "."},
                "tail": {"type": "integer", "description": "Number of log lines to retrieve.", "default": 100}
            },
            "required": ["session_id", "action"]
        }
    ),
    "ssh_generate_key": Tool(
        name="ssh_generate_key",
        description="Generate a new SSH key pair (RSA or Ed25519) for secure key-based authentication. Optionally save to a file path.",
        inputSchema={
            "type": "object",
            "properties": {
                "key_type": {"type": "string", "enum": ["rsa", "ed25519"], "default": "ed25519", "description": "Key algorithm type."},
                "key_size": {"type": "integer", "description": "Key size for RSA.", "default": 4096},
                "comment": {"type": "string", "description": "Optional comment to identify the key."},
                "save_path": {"type": "string", "description": "Optional path to save the generated key files."}
            }
        }
    ),
    "ssh_session": Tool(
        name="ssh_session",
        description="Manage persistent screen/tmux sessions on the remote server for long-running interactive tasks (deploy, build, test, REPL). Sessions survive SSH disconnect. Actions: create (new detached session running a command), send (send keys/command to a session), capture (read current screen), list (list sessions), kill (kill a session).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active SSH session ID. If omitted, connects via name/host/env vars."},
                "host_name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name. Alternative to session_id."},
                "host": {"type": "string", "description": "SSH server hostname or IP. Alternative to session_id/host_name, can override hosts.json entry."},
                "port": {"type": "integer", "description": "SSH port (used with host).", "default": 22},
                "username": {"type": "string", "description": "SSH username (used with host)."},
                "password": {"type": "string", "description": "SSH password (used with host)."},
                "action": {"type": "string", "enum": ["create", "send", "capture", "list", "kill"], "description": "create=new detached session, send=send keys/command to a session, capture=read current screen content, list=list sessions, kill=kill a session."},
                "name": {"type": "string", "description": "Session name. Required for create/send/capture/kill. Only letters, digits, _, ., - allowed."},
                "command": {"type": "string", "description": "Command to run initially (create) or to send (send)."},
                "session_type": {"type": "string", "enum": ["screen", "tmux"], "default": "screen", "description": "Use screen or tmux backend."},
                "lines": {"type": "integer", "default": 50, "description": "Number of lines to capture (tmux capture-pane -S)."}
            },
            "required": ["session_id", "action"]
        }
    ),
    "ssh_process": Tool(
        name="ssh_process",
        description="Manage background processes and SSH tunnels on the remote server. Actions: start (launch a detached background process, returns PID), stop (stop a process by PID), status (check if a PID is running), list (list tracked background tasks), tunnel_open (local port forward to remote host:port), tunnel_close (close a tunnel), tunnel_list (list active tunnels).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active SSH session ID. If omitted, connects via name/host/env vars."},
                "name": {"type": "string", "description": "Use a pre-configured host from hosts.json by name. Alternative to session_id."},
                "host": {"type": "string", "description": "SSH server hostname or IP. Alternative to session_id/name, can override hosts.json entry."},
                "port": {"type": "integer", "description": "SSH port (used with host).", "default": 22},
                "username": {"type": "string", "description": "SSH username (used with host)."},
                "password": {"type": "string", "description": "SSH password (used with host)."},
                "action": {"type": "string", "enum": ["start", "stop", "status", "list", "tunnel_open", "tunnel_close", "tunnel_list"], "description": "Process/tunnel action."},
                "command": {"type": "string", "description": "Command to run (start)."},
                "pid": {"type": "string", "description": "Process ID (stop/status)."},
                "task_id": {"type": "string", "description": "Task ID (stop/status, alternative to pid)."},
                "signal": {"type": "string", "default": "TERM", "description": "Signal to send on stop (TERM, KILL, INT, etc.)."},
                "workdir": {"type": "string", "default": "/tmp", "description": "Working directory (start)."},
                "log_file": {"type": "string", "description": "Log file path (start). Default /tmp/bg_<taskid>.log"},
                "local_port": {"type": "integer", "description": "Local listen port (tunnel_open)."},
                "remote_host": {"type": "string", "description": "Remote target host (tunnel_open)."},
                "remote_port": {"type": "integer", "description": "Remote target port (tunnel_open)."}
            },
            "required": ["session_id", "action"]
        }
    ),
    "ssh_request_approval": Tool(
        name="ssh_request_approval",
        description="加固点 4：高危操作审批 — AI 提交审批申请。当 SSH_APPROVAL_GATE=true 时，rm -rf、reboot、iptables 等高危命令必须先调用本工具申请审批，获得 approval_id 后再调用 ssh_execute 携带 approval_id 执行。AI 不能直接下发高危命令。",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "需要审批的高危命令（必须与后续 ssh_execute 的 command 完全一致，否则校验失败）。"},
                "reason": {"type": "string", "description": "申请理由：为什么需要执行此高危命令、预期影响、回滚方案。"}
            },
            "required": ["command", "reason"]
        }
    ),
    "ssh_approve_command": Tool(
        name="ssh_approve_command",
        description="加固点 4：高危操作审批 — 运维人员人工审批 AI 提交的申请。返回审批结果。审批通过后 AI 可用获得的 approval_id 执行命令（一次性，用后即焚）。",
        inputSchema={
            "type": "object",
            "properties": {
                "approval_id": {"type": "string", "description": "待审批的 approval_id（由 ssh_request_approval 返回）。"},
                "decision": {"type": "string", "enum": ["approved", "rejected"], "description": "审批决定：approved=同意执行，rejected=拒绝。"},
                "reviewer": {"type": "string", "description": "审批人标识（运维人员姓名/账号），用于审计。"},
                "comment": {"type": "string", "description": "审批意见（可选）。"}
            },
            "required": ["approval_id", "decision", "reviewer"]
        }
    ),
    "ssh_list_approvals": Tool(
        name="ssh_list_approvals",
        description="加固点 4：高危操作审批 — 列出审批记录。运维人员查看待处理队列或历史记录。action=pending 只看待审批，action=all 查看全部（最近 100 条）。",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["pending", "all"], "default": "pending", "description": "pending=仅待审批，all=全部记录（最近 100 条）。"}
            }
        }
    ),
}
