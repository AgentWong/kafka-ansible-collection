# Kafka Ansible Collection
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An Ansible collection for deploying production-grade Apache Kafka clusters with ZooKeeper coordination and TLS security. This project demonstrates AI-assisted development methodology with comprehensive Molecule testing.

LinkedIn Article Writeup:
- https://www.linkedin.com/pulse/how-i-get-10x-more-value-from-github-copilot-using-one-herman-wong-3xotc/

Video Demo:
- https://www.youtube.com/watch?v=qMzQdLTZNAQ
  - Full length, 37:06
- https://vimeo.com/1153847231
  - Trimmed, 1.25x speed, 22:14

## 🎯 Features

- **Production-grade Kafka deployment** with 3-node broker cluster
- **ZooKeeper ensemble** (3 nodes) for cluster coordination
- **TLS encryption** with self-signed Root CA for secure communications
- **Multi-platform support** for Rocky Linux 9 and Ubuntu 22.04
- **Comprehensive testing** using Molecule with systemd-enabled containers
- **AI-assisted development** workflow demonstration

## 📋 Architecture

```mermaid
graph TB
    subgraph "Kafka Cluster Infrastructure"
        CA[Root CA<br/>rootca1<br/>Certificate Authority]

        subgraph "ZooKeeper Ensemble"
            ZK1[ZooKeeper 1<br/>zk1<br/>:2181, :2888, :3888]
            ZK2[ZooKeeper 2<br/>zk2<br/>:2181, :2888, :3888]
            ZK3[ZooKeeper 3<br/>zk3<br/>:2181, :2888, :3888]
        end

        subgraph "Kafka Brokers"
            K1[Kafka Broker 1<br/>kafka1<br/>:9092 PLAINTEXT<br/>:9093 SSL]
            K2[Kafka Broker 2<br/>kafka2<br/>:9092 PLAINTEXT<br/>:9093 SSL]
            K3[Kafka Broker 3<br/>kafka3<br/>:9092 PLAINTEXT<br/>:9093 SSL]
        end

        UI[Kafka UI<br/>kafkaui1<br/>:8080<br/>Web Management Console]
    end

    CA -.->|Issues TLS Certificates| ZK1
    CA -.->|Issues TLS Certificates| ZK2
    CA -.->|Issues TLS Certificates| ZK3
    CA -.->|Issues TLS Certificates| K1
    CA -.->|Issues TLS Certificates| K2
    CA -.->|Issues TLS Certificates| K3

    ZK1 <-->|Quorum| ZK2
    ZK2 <-->|Quorum| ZK3
    ZK3 <-->|Quorum| ZK1

    K1 -->|Coordination :2181| ZK1
    K1 -->|Coordination :2181| ZK2
    K1 -->|Coordination :2181| ZK3

    K2 -->|Coordination :2181| ZK1
    K2 -->|Coordination :2181| ZK2
    K2 -->|Coordination :2181| ZK3

    K3 -->|Coordination :2181| ZK1
    K3 -->|Coordination :2181| ZK2
    K3 -->|Coordination :2181| ZK3

    K1 <-->|Replication| K2
    K2 <-->|Replication| K3
    K3 <-->|Replication| K1

    UI -->|Monitors :9092| K1
    UI -->|Monitors :9092| K2
    UI -->|Monitors :9092| K3

    style CA fill:#f9f,stroke:#333,stroke-width:2px
    style UI fill:#bbf,stroke:#333,stroke-width:2px
    style ZK1 fill:#bfb,stroke:#333,stroke-width:2px
    style ZK2 fill:#bfb,stroke:#333,stroke-width:2px
    style ZK3 fill:#bfb,stroke:#333,stroke-width:2px
    style K1 fill:#fbb,stroke:#333,stroke-width:2px
    style K2 fill:#fbb,stroke:#333,stroke-width:2px
    style K3 fill:#fbb,stroke:#333,stroke-width:2px
```

**Total Nodes:** 8 (1 CA + 3 ZooKeeper + 3 Kafka brokers + 1 Kafka UI)

### Component Overview

- **Root CA (rootca1)**: Generates self-signed certificates for TLS encryption
- **ZooKeeper Ensemble (zk1-3)**: Distributed coordination service for Kafka cluster
- **Kafka Brokers (kafka1-3)**: Message storage and streaming platform
- **Kafka UI (kafkaui1)**: Web-based management and monitoring interface at [http://localhost:8080](http://localhost:8080)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for Molecule testing)
- Ansible Core 2.15+

### Installation

```bash
# Clone the repository
git clone https://github.com/AgentWong/kafka-ansible-collection.git
cd kafka-ansible-collection

# Install Python dependencies
pip install -r requirements.txt

# Install Ansible Galaxy dependencies
ansible-galaxy collection install -r requirements.yml
```

### Running Tests

```bash
# Run full Molecule test suite
molecule test

# Run converge only (for development)
molecule converge

# Verify cluster health
molecule verify

# Destroy test environment
molecule destroy
```

## 📦 Roles

| Role | Description |
|------|-------------|
| `common` | Base system configuration, packages, users, and directories |
| `java` | OpenJDK installation (Java 11 or 17) |
| `rootca` | Self-signed Root CA certificate generation |
| `zookeeper` | Apache ZooKeeper cluster deployment with TLS |
| `kafka` | Apache Kafka broker deployment with TLS |

## 🔧 Configuration

### Key Variables

```yaml
# Java
java_version: "17"

# ZooKeeper
zookeeper_version: "3.9.3"
zookeeper_client_port: 2181
zookeeper_tls_enabled: true

# Kafka
kafka_version: "3.7.0"
kafka_tls_enabled: true
kafka_listeners:
  - PLAINTEXT://:9092
  - SSL://:9093
```

See individual role `defaults/main.yml` files for complete variable documentation.

## 📁 Repository Structure

```
kafka-ansible-collection/
├── containers/          # Custom systemd-enabled Docker images
├── docs/               # Additional documentation
├── extensions/molecule/ # Molecule testing configuration
├── inventory/          # Sample inventory files
├── playbooks/          # Deployment playbooks
├── plugins/            # Custom Ansible plugins
└── roles/              # Ansible roles
    ├── common/
    ├── java/
    ├── kafka/
    ├── rootca/
    └── zookeeper/
```

## 🧪 Testing

This project uses Molecule with custom systemd-enabled Docker containers for comprehensive testing. The test infrastructure supports:

- **Rocky Linux 9** - Primary testing platform (RHEL alternative)
- **Ubuntu 22.04** - Secondary testing platform

Tests validate:
- Service installation and configuration
- Cluster formation and leader election
- TLS certificate generation and distribution
- Inter-node communication
- Message production and consumption

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Herman Wong**

- GitHub: [@AgentWong](https://github.com/AgentWong)

## 🙏 Acknowledgments

- Apache Kafka and ZooKeeper communities
- Ansible and Molecule development teams
- GitHub Copilot for AI-assisted development