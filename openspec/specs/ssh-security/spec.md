# ssh-security Specification

## Purpose

Provide security mechanisms for the SSH MCP server including command validation, rate limiting, audit logging, and path validation.
## Requirements
### Requirement: Command Validation

The system SHALL validate all commands before execution to prevent command injection and unauthorized operations.

#### Scenario: Safe command allowed

- GIVEN a command is submitted for execution
- WHEN the command passes all validation rules
- THEN the system SHALL allow the command to execute

#### Scenario: Dangerous command blocked

- GIVEN a command contains dangerous patterns (e.g., "rm -rf /", "mkfs", "dd if=/dev/zero")
- WHEN the command is submitted for execution
- THEN the system SHALL block the command
- AND return a security error with remediation guidance

#### Scenario: Shell operator validation

- GIVEN SSH_SECURITY_LEVEL is set
- WHEN a command contains shell operators (|, &, ;, >, <)
- THEN the system SHALL validate based on the security level
- AND block or allow accordingly

### Requirement: Rate Limiting

The system SHALL enforce rate limiting using a sliding window algorithm to prevent denial-of-service attacks.

#### Scenario: Within rate limit

- GIVEN the number of requests in the current time window is below SSH_RATE_LIMIT_MAX
- WHEN a new request is submitted
- THEN the system SHALL process the request normally

#### Scenario: Rate limit exceeded

- GIVEN the number of requests in the current time window has reached SSH_RATE_LIMIT_MAX
- WHEN a new request is submitted
- THEN the system SHALL reject the request
- AND return a rate limit error message with configuration guidance

#### Scenario: Rate limit disabled

- GIVEN SSH_RATE_LIMIT=false
- WHEN any number of requests are submitted
- THEN the system SHALL process all requests without rate limiting

### Requirement: Audit Logging

The system SHALL support optional audit logging for SSH operations.

#### Scenario: Audit connection events

- GIVEN SSH_AUDIT_LOG_PATH is configured
- WHEN an SSH connection is established or fails
- THEN the system SHALL log the event with username, host, port, client_type, and success status

#### Scenario: Audit command execution

- GIVEN SSH_AUDIT_LOG_PATH is configured
- WHEN a command is executed on a remote server
- THEN the system SHALL log the command, return code, and execution time

#### Scenario: Audit logging disabled

- GIVEN SSH_AUDIT_LOG_PATH is not set
- WHEN SSH operations are performed
- THEN the system SHALL NOT write audit logs

### Requirement: Path Validation

The system SHALL validate file paths used in background tasks and file operations.

#### Scenario: Safe path allowed

- GIVEN a path is within allowed directories
- WHEN a file operation is requested
- THEN the system SHALL allow the operation

#### Scenario: Unsafe path blocked

- GIVEN a path is outside allowed directories or contains traversal patterns
- WHEN a file operation is requested
- THEN the system SHALL block the operation with a security error

### Requirement: Password Masking

The system SHALL mask passwords in all responses and logs.

#### Scenario: Password in connection response

- GIVEN a successful SSH connection is established
- WHEN the response is returned to the client
- THEN the password SHALL be masked as "***"

#### Scenario: Password in host listing

- GIVEN hosts with passwords are listed
- WHEN ssh_list_hosts returns host details
- THEN all passwords SHALL be displayed as "***" or "已设置"

### Requirement: Input Validation for Docker Operations

The system SHALL validate Docker-related inputs to prevent injection attacks.

#### Scenario: Valid image name

- GIVEN an image name matches the pattern [a-zA-Z0-9][a-zA-Z0-9_./:-]*
- WHEN a Docker operation is requested
- THEN the system SHALL allow the operation

#### Scenario: Invalid image name

- GIVEN an image name contains special characters
- WHEN a Docker operation is requested
- THEN the system SHALL reject the request with a validation error

#### Scenario: Valid container name

- GIVEN a container name matches the pattern [a-zA-Z0-9][a-zA-Z0-9_.-]*
- WHEN a container operation is requested
- THEN the system SHALL allow the operation

#### Scenario: Invalid container name

- GIVEN a container name contains special characters
- WHEN a container operation is requested
- THEN the system SHALL reject the request with a validation error

### Requirement: Hard Block on Catastrophic Commands

The system SHALL reject any command whose text matches the catastrophic-operation pattern set before any other validation step executes. The rejection MUST be unconditional: it MUST NOT depend on `SSH_SECURITY_LEVEL`, `confirm_dangerous`, `confirmation_layer`, or any other runtime parameter. The rejection MUST apply in all three security levels (`strict`, `balanced`, `relaxed`).

The catastrophic-operation pattern set MUST include, at minimum:

- `rm -rf /`, `rm -rf /*`, `rm -rf /<abs-path>`, `rm -rf /<abs-path>/*` (any absolute-path recursive delete)
- `mkfs.<fstype>` (any filesystem format invocation)
- `dd if=/dev/(zero|random|urandom) of=/dev/(sd|nvme)` (raw-disk overwrite)
- `:(){:|:&};:` and any whitespace variant of the bash fork-bomb
- `chmod -R (777|000) /` (recursive root-permission change)
- `> /dev/(sd|nvme)` and `>> /dev/(sd|nvme)` (raw redirect to disk device)

#### Scenario: rm -rf on absolute path is rejected in balanced mode without confirm

- **WHEN** a caller submits `rm -rf /etc` via `ssh_execute` with `SSH_SECURITY_LEVEL=balanced` and `confirm_dangerous` omitted
- **THEN** the system SHALL return a hard-block error and SHALL NOT execute the command on the remote server

#### Scenario: rm -rf on absolute path is rejected even with confirm_dangerous=true

- **WHEN** a caller submits `rm -rf /var/lib/postgresql/data` with `confirm_dangerous=true` and `confirmation_layer=3`
- **THEN** the system SHALL return a hard-block error
- **AND** the error message SHALL NOT mention any override path

#### Scenario: rm -rf on absolute path is rejected in relaxed mode

- **WHEN** a caller submits `rm -rf /home/user/junk` with `SSH_SECURITY_LEVEL=relaxed`
- **THEN** the system SHALL return a hard-block error

#### Scenario: mkfs is rejected in all modes

- **WHEN** a caller submits `mkfs.ext4 /dev/sda1` under any `SSH_SECURITY_LEVEL`
- **THEN** the system SHALL return a hard-block error

#### Scenario: raw-disk dd is rejected in all modes

- **WHEN** a caller submits `dd if=/dev/zero of=/dev/nvme0n1 bs=1M`
- **THEN** the system SHALL return a hard-block error

#### Scenario: bash fork-bomb is rejected in all modes

- **WHEN** a caller submits the bash fork-bomb `:(){:|:&};:` under any `SSH_SECURITY_LEVEL`
- **THEN** the system SHALL return a hard-block error

#### Scenario: root chmod 777 is rejected in all modes

- **WHEN** a caller submits `chmod -R 777 /`
- **THEN** the system SHALL return a hard-block error

#### Scenario: hard-block hit is logged as WARNING

- **WHEN** the hard-block check rejects a command
- **THEN** the system SHALL emit a `WARNING` log line containing the command text and a non-regex marker for the matched pattern category
- **AND** the log line SHALL NOT echo the regex itself

#### Scenario: safe single-file delete continues to work

- **WHEN** a caller submits `rm /tmp/test.log` under any `SSH_SECURITY_LEVEL`
- **THEN** the system SHALL allow the command to execute

#### Scenario: empty-directory rmdir continues to work

- **WHEN** a caller submits `rmdir /tmp/empty_dir` under any `SSH_SECURITY_LEVEL`
- **THEN** the system SHALL allow the command to execute

#### Scenario: relative-path rm -rf remains under soft gate (regression guard)

- **WHEN** a caller submits `rm -rf ./build/` with `SSH_SECURITY_LEVEL=balanced` and `confirm_dangerous=true, confirmation_layer=2`
- **THEN** the system SHALL allow the command to execute
- **AND** the soft multi-layer confirmation SHALL continue to function unchanged for non-hard-blocked commands

