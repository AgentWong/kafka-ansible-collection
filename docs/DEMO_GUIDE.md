# Interview Demo Guide

This guide provides instructions for demonstrating the Kafka Ansible Collection during job interviews.

## Demo Overview

**Duration:** 15-20 minutes

**Objectives:**
1. Showcase Ansible automation skills
2. Demonstrate AI-assisted development methodology
3. Show understanding of distributed systems (Kafka, ZooKeeper)
4. Highlight testing best practices with Molecule

## Pre-Demo Setup

### Environment Preparation

1. **Start Docker Desktop** (if not running)
2. **Open VS Code** with project loaded
3. **Ensure terminal is ready** with venv activated
4. **Pre-build containers** (optional, saves time):

```bash
cd extensions/molecule/default
molecule create
```

## Demo Script

### Part 1: Project Introduction (2-3 minutes)

**Talking Points:**
- "This is an Ansible collection for deploying Apache Kafka clusters"
- "It demonstrates production-grade automation with TLS security"
- "Built using AI-assisted development with GitHub Copilot"

**Show:**
- README.md with architecture diagram
- Repository structure
- galaxy.yml collection metadata

### Part 2: Role Walkthrough (3-4 minutes)

**Navigate to roles directory and explain:**

```
roles/
├── common/      # Base system config
├── java/        # Java installation
├── rootca/      # TLS certificates
├── zookeeper/   # ZooKeeper cluster
└── kafka/       # Kafka brokers
```

**Highlight key files:**
- `roles/zookeeper/defaults/main.yml` - Variable documentation
- `roles/zookeeper/templates/zoo.cfg.j2` - Cluster configuration
- `roles/kafka/templates/server.properties.j2` - Kafka configuration

### Part 3: Live Demo with Molecule (5-7 minutes)

**Run the deployment:**

```bash
cd extensions/molecule/default
molecule converge
```

**While running, explain:**
- Custom systemd-enabled Docker containers
- Shared state across 7 nodes
- TLS certificate generation in prepare phase
- Role execution order (common → java → zookeeper → kafka)

### Part 4: Verification (2-3 minutes)

**Run verification:**

```bash
molecule verify
```

**Show cluster health:**
- ZooKeeper quorum status
- Kafka broker connectivity
- Service status checks

### Part 5: AI-Assisted Development Demo (3-5 minutes)

**Demonstrate debugging workflow:**

1. **Intentionally break something:**
   - Comment out a required task
   - Introduce a syntax error
   - Use wrong variable name

2. **Show the error:**
   ```bash
   molecule converge
   ```

3. **Use Copilot to debug:**
   - Copy error message
   - Ask for analysis
   - Apply suggested fix

4. **Verify the fix:**
   ```bash
   molecule converge
   ```

## Key Talking Points

### Technical Depth

- **Cluster coordination:** ZooKeeper handles leader election
- **Data replication:** Kafka replicates across 3 brokers
- **TLS security:** Self-signed CA for encrypted communication
- **Idempotency:** Can run playbooks multiple times safely

### Best Practices Demonstrated

- **Modular roles:** Each component is independently testable
- **OS abstraction:** Variables handle Rocky Linux vs Ubuntu
- **Security hardening:** systemd service with security options
- **Comprehensive testing:** Full cluster verified with Molecule

### AI-Assisted Development

- **Rapid prototyping:** Generate boilerplate quickly
- **Error analysis:** AI helps interpret complex errors
- **Best practices:** AI suggests improvements
- **Documentation:** AI helps write clear docs

## Cleanup

After the demo:

```bash
molecule destroy
```

## Troubleshooting

### Container Build Slow

Pre-build before the demo:
```bash
docker build -t kafka-ansible/rocky9-systemd containers/rocky/9/
```

### Network Issues

If containers can't communicate:
```bash
molecule destroy
docker network prune
molecule create
```

### Service Start Failures

Check logs inside container:
```bash
molecule login -h zk1
journalctl -u zookeeper -f
```
