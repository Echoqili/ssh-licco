# ssh-security Delta Spec — Hard-Block Dangerous Commands

## ADDED Requirements

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
