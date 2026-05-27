# ssh-docker-management Specification

## Purpose

Manage Docker operations on remote SSH servers including image building, container status checking, and log retrieval.

## Requirements

### Requirement: Docker Image Build

The system SHALL support building Docker images on remote servers in background mode.

#### Scenario: Build a Docker image

- GIVEN an active SSH session exists
- WHEN ssh_docker_build is called with image_name and optional dockerfile_path
- THEN the system SHALL start a background Docker build task
- AND return a task_id for monitoring the build progress

#### Scenario: Build with default Dockerfile

- GIVEN an active SSH session exists
- WHEN ssh_docker_build is called with only image_name
- THEN the system SHALL use "./Dockerfile" as the default Dockerfile path
- AND use "." as the default build context

### Requirement: Docker Status Check

The system SHALL support checking Docker container and image status on remote servers.

#### Scenario: Check all Docker containers

- GIVEN an active SSH session exists
- WHEN ssh_docker_status is called with only session_id
- THEN the system SHALL list all running Docker containers
- AND show recent build logs if available

#### Scenario: Check specific Docker image

- GIVEN an active SSH session exists
- WHEN ssh_docker_status is called with image_name
- THEN the system SHALL list containers and show matching Docker images
- AND validate the image_name format for security

### Requirement: Container Log Retrieval

The system SHALL support retrieving Docker container logs with tailing and time filtering.

#### Scenario: Get container logs

- GIVEN an active SSH session exists
- WHEN ssh_container_logs is called with container_name
- THEN the system SHALL retrieve the last 100 lines of container logs by default
- AND include the container status

#### Scenario: Get logs with custom tail

- GIVEN an active SSH session exists
- WHEN ssh_container_logs is called with container_name and tail=50
- THEN the system SHALL retrieve the last 50 lines of container logs

#### Scenario: Invalid container name

- GIVEN an active SSH session exists
- WHEN ssh_container_logs is called with a container_name containing special characters
- THEN the system SHALL reject the request with a validation error
