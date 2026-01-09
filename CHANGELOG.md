# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure for Kafka Ansible collection
- Custom systemd-enabled Docker containers for Rocky Linux 9 and Ubuntu 22.04
- Molecule testing framework with shared state configuration
- `common` role for base system configuration
- `java` role for OpenJDK installation
- `rootca` role for TLS certificate generation
- `zookeeper` role for Apache ZooKeeper cluster deployment
- `kafka` role for Apache Kafka broker deployment

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- TLS encryption for all Kafka and ZooKeeper communications
