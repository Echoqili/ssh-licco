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
