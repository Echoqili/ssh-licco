# ssh-file-transfer Specification

## Purpose

Transfer files between local and remote servers via SFTP, supporting upload, download, and directory listing.

## Requirements

### Requirement: File Upload

The system SHALL support uploading files from the local machine to a remote SSH server.

#### Scenario: Upload a file

- GIVEN an active SSH session exists
- WHEN ssh_file_transfer is called with direction="upload", local_path, and remote_path
- THEN the system SHALL transfer the file from local_path to remote_path via SFTP
- AND return a success or failure message

### Requirement: File Download

The system SHALL support downloading files from a remote SSH server to the local machine.

#### Scenario: Download a file

- GIVEN an active SSH session exists
- WHEN ssh_file_transfer is called with direction="download", local_path, and remote_path
- THEN the system SHALL transfer the file from remote_path to local_path via SFTP
- AND return a success or failure message

### Requirement: Directory Listing

The system SHALL support listing files and directories on a remote server.

#### Scenario: List directory contents

- GIVEN an active SSH session exists
- WHEN ssh_file_transfer is called with direction="list" and remote_path
- THEN the system SHALL list the contents of the remote directory
- AND return a list of files and subdirectories

### Requirement: Transfer Error Handling

The system SHALL handle file transfer errors gracefully.

#### Scenario: File not found on remote server

- GIVEN an active SSH session exists
- WHEN ssh_file_transfer is called with a remote_path that does not exist
- THEN the system SHALL return an error message indicating the file was not found

#### Scenario: Permission denied

- GIVEN an active SSH session exists
- WHEN ssh_file_transfer is called with a path the user does not have access to
- THEN the system SHALL return a permission denied error
