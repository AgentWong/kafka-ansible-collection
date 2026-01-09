# Custom Systemd-Enabled Docker Containers

This directory contains custom Docker container definitions for Molecule testing. These containers support systemd, which is required for testing services like ZooKeeper and Kafka.

## Supported Platforms

| Platform | Version | Architecture | Directory |
|----------|---------|--------------|-----------|
| Rocky Linux | 9 | amd64, arm64 | `rocky/9/` |
| Ubuntu | 22.04 | amd64, arm64 | `ubuntu/22/` |

## Features

All containers include:

- **Systemd enabled** - Full systemd support for service management
- **Ansible user** - Pre-configured `ansible` user with sudo access
- **Python 3.11** - Required for Ansible execution
- **OpenSSL** - For TLS certificate operations
- **Common utilities** - wget, curl, tar, nc, etc.

## Building Containers

Containers are automatically built by Molecule during test execution. To build manually:

```bash
# Rocky Linux 9
docker build -t kafka-ansible/rocky9-systemd containers/rocky/9/

# Ubuntu 22.04
docker build -t kafka-ansible/ubuntu22-systemd containers/ubuntu/22/
```

## Container Requirements

For systemd to work properly, containers must be run with:

- `--privileged` flag OR appropriate capabilities
- `/sys/fs/cgroup` volume mount
- `cgroupns: host` setting

These settings are configured automatically in the Molecule `molecule.yml` configuration.

## Architecture Notes

- Containers are built to support both **amd64** (Intel/AMD) and **arm64** (Apple Silicon) architectures
- The Dockerfiles use multi-stage builds where appropriate for smaller image sizes
