---
name: kafka-troubleshooting
description: Troubleshoot Kafka, ZooKeeper, and Broker issues. Use when debugging service failures, connection issues, or unexpected errors in the Kafka cluster.
---

# Kafka Cluster Troubleshooting

This skill helps diagnose and fix issues with Kafka brokers, ZooKeeper ensemble, and related services.

## When to Use This Skill

- Kafka broker fails to start or crashes
- ZooKeeper connection issues
- Consumer/producer connectivity problems
- TLS/SSL certificate errors
- Cluster coordination failures

## Container Access

**IMPORTANT**: Use `docker exec` instead of `molecule login` for non-interactive troubleshooting.

`molecule login` requires an interactive shell which is not suitable for automated troubleshooting.

```bash
# Get container names
docker ps --format "table {{.Names}}\t{{.Status}}"

# Execute commands in containers
docker exec <container_name> <command>
```

## Log File Locations

### ZooKeeper Logs

```bash
# ZooKeeper logs (when installed via tarball)
docker exec zk1 cat /opt/zookeeper/logs/zookeeper-root-server-zk1.out
docker exec zk1 tail -50 /opt/zookeeper/logs/zookeeper-root-server-zk1.out

# ZooKeeper logs (systemd journal)
docker exec zk1 journalctl -u zookeeper -n 50 --no-pager

# Check ZooKeeper status
docker exec zk1 /opt/zookeeper/bin/zkServer.sh status
```

### Kafka Broker Logs

```bash
# Kafka server logs (when installed via tarball)
docker exec kafka1 cat /opt/kafka/logs/server.log
docker exec kafka1 tail -100 /opt/kafka/logs/server.log

# Kafka logs (systemd journal)
docker exec kafka1 journalctl -u kafka -n 50 --no-pager

# Check if Kafka is responding
docker exec kafka1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

### System Logs

```bash
# General system journal
docker exec kafka1 journalctl -xe --no-pager | tail -50
```

## Common Diagnostic Commands

### ZooKeeper Health

```bash
# Check ZooKeeper mode (leader/follower)
docker exec zk1 /opt/zookeeper/bin/zkServer.sh status

# Test ZooKeeper connectivity with 4-letter commands
docker exec zk1 bash -c 'echo ruok | nc localhost 2181'
docker exec zk1 bash -c 'echo stat | nc localhost 2181'

# List ZooKeeper znodes
docker exec zk1 /opt/zookeeper/bin/zkCli.sh -server localhost:2181 ls /
```

### Kafka Health

```bash
# List topics
docker exec kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# Describe cluster
docker exec kafka1 /opt/kafka/bin/kafka-metadata.sh --snapshot /var/kafka-logs/__cluster_metadata-0/00000000000000000000.log --command "describe"

# Check broker API versions
docker exec kafka1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Check consumer groups
docker exec kafka1 /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

### Network/Port Verification

```bash
# Check listening ports
docker exec kafka1 ss -tlnp
docker exec zk1 ss -tlnp

# Test ZooKeeper port from Kafka broker
docker exec kafka1 bash -c 'nc -zv zk1 2181'
```

### Process Status

```bash
# Check Java processes
docker exec kafka1 jps -l
docker exec zk1 jps -l

# Check systemd service status
docker exec kafka1 systemctl status kafka
docker exec zk1 systemctl status zookeeper
```

## Common Issues and Solutions

### Issue: ZooKeeper Won't Form Quorum

**Symptoms**: `zkServer.sh status` shows "Error contacting service"

**Check**:
```bash
# Verify myid file
docker exec zk1 cat /var/lib/zookeeper/myid

# Check zoo.cfg has correct server entries
docker exec zk1 cat /opt/zookeeper/conf/zoo.cfg
```

### Issue: Kafka Cannot Connect to ZooKeeper

**Symptoms**: Kafka logs show "Connection refused" to ZooKeeper

**Check**:
```bash
# Test connectivity from Kafka to each ZK node
docker exec kafka1 bash -c 'for zk in zk1 zk2 zk3; do echo -n "$zk: "; nc -zv $zk 2181 2>&1; done'

# Verify zookeeper.connect in server.properties
docker exec kafka1 grep zookeeper.connect /opt/kafka/config/server.properties
```

### Issue: TLS/SSL Certificate Errors

**Symptoms**: SSL handshake failures in logs

**Check**:
```bash
# Verify keystore exists
docker exec kafka1 ls -la /opt/kafka/config/*.jks

# Check certificate validity
docker exec kafka1 keytool -list -v -keystore /opt/kafka/config/kafka.keystore.jks -storepass <password> | grep -A2 "Valid from"
```

## Filtering Ansible Output

When running Molecule commands, always filter to avoid context window bloat:

```bash
# Show only failures and summary
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario)" -A 15

# Show more context around failures
molecule converge 2>&1 | grep -B 5 -A 25 "fatal:"
```
