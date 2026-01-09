# Architecture Documentation

## Overview

This Ansible collection deploys a production-grade Apache Kafka cluster with ZooKeeper coordination and TLS security.

## Cluster Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Kafka Cluster                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────┐                                                   │
│  │   Root CA   │  ← Self-signed CA for TLS certificate generation │
│  │  (rootca1)  │                                                   │
│  └──────┬──────┘                                                   │
│         │                                                          │
│         │ Issues TLS certs for ↓                                   │
│         │                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ ZooKeeper 1 │  │ ZooKeeper 2 │  │ ZooKeeper 3 │                │
│  │   (zk1)     │  │   (zk2)     │  │   (zk3)     │                │
│  │             │  │             │  │             │                │
│  │ ZK: 2181    │  │ ZK: 2181    │  │ ZK: 2181    │                │
│  │     2888    │  │     2888    │  │     2888    │                │
│  │     3888    │  │     3888    │  │     3888    │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
│         │                │                │                        │
│         └────────────────┼────────────────┘                        │
│                          │                                         │
│                          ↓                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Broker 1   │  │  Broker 2   │  │  Broker 3   │                │
│  │  (kafka1)   │  │  (kafka2)   │  │  (kafka3)   │                │
│  │             │  │             │  │             │                │
│  │ Kafka: 9092 │  │ Kafka: 9092 │  │ Kafka: 9092 │                │
│  │        9093 │  │        9093 │  │        9093 │ (TLS)          │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Root CA (1 node)

- Generates self-signed CA certificate
- Issues TLS certificates for all cluster nodes
- Creates PKCS12 keystores for Java applications

### ZooKeeper Ensemble (3 nodes)

- Provides distributed coordination for Kafka
- Handles leader election and cluster membership
- Stores cluster metadata and configurations

**Ports:**
- 2181: Client connections
- 2888: Follower-to-leader communication
- 3888: Leader election

### Kafka Brokers (3 nodes)

- Store and serve messages
- Handle producer and consumer requests
- Replicate data across the cluster

**Ports:**
- 9092: PLAINTEXT listener
- 9093: SSL/TLS listener

## Network Communication

### ZooKeeper Quorum

All ZooKeeper nodes communicate with each other:
- Port 2888 for follower-to-leader data sync
- Port 3888 for leader election

### Kafka to ZooKeeper

All Kafka brokers connect to ZooKeeper:
- Port 2181 for cluster coordination
- Connection string format: `zk1:2181,zk2:2181,zk3:2181`

### Kafka Inter-Broker

Brokers replicate data between each other:
- Uses configured listener (PLAINTEXT or SSL)
- Replication factor determines number of copies

## TLS Security

When TLS is enabled:

1. **Root CA** generates certificates for all nodes
2. **Keystores** contain private keys and certificates
3. **Truststores** contain the CA certificate
4. All communication is encrypted

### Certificate Distribution

```
rootca1 generates:
  ├── ca.crt (CA certificate)
  ├── ca.key (CA private key)
  │
  └── For each node:
      ├── {hostname}.key (private key)
      ├── {hostname}.crt (signed certificate)
      └── {hostname}.p12 (PKCS12 keystore)
```

## Resource Requirements

### Minimum (Testing)

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| ZooKeeper | 1 | 512MB | 10GB |
| Kafka | 1 | 1GB | 20GB |

### Production

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| ZooKeeper | 2 | 2GB | 50GB SSD |
| Kafka | 4 | 8GB | 500GB SSD |
