# ssh-connection Specification

## Purpose

Manage SSH connections to remote servers including configuration, authentication, and connection lifecycle.

## Requirements

### Requirement: SSH Connection Configuration

The system SHALL allow users to configure SSH connection settings (host, port, username, password) and persist them to a local config file.

#### Scenario: Save SSH configuration

- GIVEN a user provides connection parameters
- WHEN ssh_config is called with host, port, username, and password
- THEN the system SHALL save the configuration to config/hosts.json
- AND return a confirmation with the saved settings (password masked)

#### Scenario: Quick login with saved config

- GIVEN a user has previously saved SSH configuration
- WHEN ssh_login is called without parameters
- THEN the system SHALL use the saved configuration to establish a connection
- AND return a session_id for subsequent operations

### Requirement: Explicit SSH Connection

The system SHALL support establishing SSH connections with explicit parameters, including password and key-based authentication.

#### Scenario: Connect with password authentication

- GIVEN a user provides host, username, and password
- WHEN ssh_connect is called with these parameters
- THEN the system SHALL establish an SSH session using password authentication
- AND return a session_id and connection details

#### Scenario: Connect with private key authentication

- GIVEN a user provides host, username, and private_key_path
- WHEN ssh_connect is called with auth_method="private_key"
- THEN the system SHALL establish an SSH session using key-based authentication
- AND return a session_id and connection details

#### Scenario: Connect using named host from config

- GIVEN a host named "production" exists in hosts.json
- WHEN ssh_connect is called with name="production"
- THEN the system SHALL load the host configuration and establish a connection
- AND return a session_id and connection details

### Requirement: Connection Priority Resolution

The system SHALL resolve connection parameters using a configurable priority order.

#### Scenario: Default priority (user parameters first)

- GIVEN SSH_FORCE_ENV_CONFIG is not set
- WHEN ssh_connect receives user parameters
- THEN user parameters SHALL take highest priority
- THEN named host config SHALL take second priority
- THEN environment variable config SHALL take lowest priority

#### Scenario: Forced environment config mode

- GIVEN SSH_FORCE_ENV_CONFIG=true
- WHEN ssh_connect is called
- THEN environment variable config SHALL override all user parameters
- AND a warning SHALL be logged indicating force mode is active

### Requirement: Host Management

The system SHALL allow users to manage SSH server configurations in hosts.json.

#### Scenario: Add a new host

- GIVEN a user provides name and host (required) plus optional parameters
- WHEN ssh_add_host is called
- THEN the system SHALL add the host entry to hosts.json
- AND return a confirmation with the host details

#### Scenario: Remove an existing host

- GIVEN a host named "staging" exists in hosts.json
- WHEN ssh_remove_host is called with name="staging"
- THEN the system SHALL remove the host entry from hosts.json
- AND return a confirmation

#### Scenario: List all configured hosts

- GIVEN multiple hosts exist in hosts.json and environment variables are set
- WHEN ssh_list_hosts is called
- THEN the system SHALL display all hosts from both sources
- AND detect and report any password conflicts between config sources
