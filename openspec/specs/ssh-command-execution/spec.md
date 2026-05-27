# ssh-command-execution Specification

## Purpose

Execute commands on remote SSH servers with security validation, timeout handling, and background execution support.

## Requirements

### Requirement: Command Execution with Security Validation

The system SHALL execute commands on remote SSH sessions after passing security validation.

#### Scenario: Execute a safe command

- GIVEN an active SSH session exists
- WHEN ssh_execute is called with a safe command (e.g., "ls -la")
- THEN the system SHALL validate the command against security rules
- AND execute the command on the remote server
- AND return the exit code, stdout, and stderr

#### Scenario: Execute a blocked command

- GIVEN an active SSH session exists
- WHEN ssh_execute is called with a dangerous command (e.g., "rm -rf /")
- THEN the system SHALL block the command
- AND return a security error with guidance on how to adjust the security policy

### Requirement: Security Levels

The system SHALL support configurable security levels for command validation.

#### Scenario: Strict mode (production)

- GIVEN SSH_SECURITY_LEVEL=strict
- WHEN a command contains shell operators (|, &, ;, >)
- THEN the system SHALL block the command

#### Scenario: Balanced mode (default)

- GIVEN SSH_SECURITY_LEVEL=balanced (or not set)
- WHEN a command contains common shell operators
- THEN the system SHALL allow the command with logging

#### Scenario: Relaxed mode (development)

- GIVEN SSH_SECURITY_LEVEL=relaxed
- WHEN any command is submitted
- THEN the system SHALL allow the command with minimal restrictions

### Requirement: Background Command Execution

The system SHALL automatically detect and run long-running commands in background mode.

#### Scenario: Auto-detect background execution

- GIVEN an active SSH session
- WHEN ssh_execute is called with a server startup command (e.g., "python app.py")
- THEN the system SHALL automatically detect the command needs background execution
- AND start the command in background mode
- AND return a confirmation with log file location

#### Scenario: Explicit background execution

- GIVEN an active SSH session
- WHEN ssh_execute is called with background=True
- THEN the system SHALL run the command in background regardless of auto-detection
- AND return immediately without waiting for completion

### Requirement: Execute with Wait

The system SHALL support executing commands with configurable timeout and waiting for completion.

#### Scenario: Execute with custom timeout

- GIVEN an active SSH session
- WHEN ssh_execute_wait is called with timeout=120
- THEN the system SHALL execute the command and wait up to 120 seconds
- AND return the complete result including exit code, stdout, and stderr

### Requirement: Background Task Management

The system SHALL support managing background tasks with task IDs for monitoring.

#### Scenario: Start a background task

- GIVEN an active SSH session
- WHEN ssh_background_task is called with a command
- THEN the system SHALL start the command in background
- AND return a task_id for monitoring

#### Scenario: Check task status

- GIVEN a background task is running
- WHEN ssh_task_status is called with the task_id
- THEN the system SHALL return the task status (RUNNING/COMPLETED/NOT_FOUND)
- AND include recent log output

### Requirement: Rate Limiting

The system SHALL enforce rate limiting to prevent command flooding.

#### Scenario: Rate limit not exceeded

- GIVEN the number of commands in the current window is below SSH_RATE_LIMIT_MAX
- WHEN a command is submitted
- THEN the system SHALL execute the command normally

#### Scenario: Rate limit exceeded

- GIVEN the number of commands in the current window has reached SSH_RATE_LIMIT_MAX
- WHEN a command is submitted
- THEN the system SHALL reject the command
- AND return a rate limit error with guidance
