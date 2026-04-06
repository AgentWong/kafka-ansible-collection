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
- JMX Exporter not exposing metrics
- Prometheus targets not UP
- Grafana dashboards blank or missing data
- Nginx 502/504 gateway errors
- Traffic generator not producing messages

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

## Observability Stack Troubleshooting

### JMX Exporter Not Exposing Metrics

**Symptoms**: `curl kafka1:7071/metrics` times out or returns nothing

```bash
# Verify Java agent loaded in Kafka JVM args
docker exec kafka1 jps -v | grep jmx_prometheus

# Check Kafka service logs for JMX startup errors
docker exec kafka1 journalctl -u kafka -n 100 --no-pager | grep -i jmx

# Confirm JMX Exporter JAR exists
docker exec kafka1 ls -la /opt/jmx-exporter/

# Confirm config file exists
docker exec kafka1 cat /opt/jmx-exporter/kafka.yml
```

**Fix**: Ensure `kafka_jmx_exporter_enabled: true` in `group_vars/all.yml`. The JMX Exporter is a Java agent — the flag must be set **before** Kafka starts. Re-run `molecule converge` to redeploy.

---

### Prometheus Targets Not UP

**Symptoms**: Prometheus UI shows targets in `DOWN` or `UNKNOWN` state

```bash
# Check Prometheus config
docker exec monitoring1 cat /etc/prometheus/prometheus.yml

# Manually test scrape reachability from monitoring1
docker exec monitoring1 curl -s http://kafka1:7071/metrics | head -5
docker exec monitoring1 curl -s http://zk1:7072/metrics | head -5
docker exec monitoring1 curl -s http://localhost:9308/metrics | head -5
docker exec monitoring1 curl -s http://kafka1:9100/metrics | head -5

# Check Prometheus service logs
docker exec monitoring1 journalctl -u prometheus -n 50 --no-pager
```

---

### Grafana Dashboards Blank

**Symptoms**: Grafana loads but panels show "No data" or "Error"

```bash
# Verify datasource is configured
docker exec monitoring1 curl -s -u admin:admin http://localhost:3000/api/datasources

# Check Prometheus is actually reachable from Grafana (same host)
docker exec monitoring1 curl -s http://localhost:9090/api/v1/query?query=up

# Verify dashboard JSON files were copied
docker exec monitoring1 ls -la /var/lib/grafana/dashboards/

# Check provisioning config
docker exec monitoring1 cat /etc/grafana/provisioning/dashboards/kafka-dashboards.yml
docker exec monitoring1 cat /etc/grafana/provisioning/datasources/prometheus.yml

# Grafana logs
docker exec monitoring1 journalctl -u grafana-server -n 50 --no-pager
```

**Common cause**: Prometheus job names in dashboards must match scrape config. Check that Prometheus job `kafka-jmx` (not `kafka_jmx`) matches the `{job=...}` filter in dashboard queries.

---

### Nginx Gateway Errors

**Symptoms**: 502 Bad Gateway or SSL errors

```bash
# Test nginx config
docker exec nginx1 nginx -t

# Check nginx error log
docker exec nginx1 cat /var/log/nginx/error.log | tail -30

# Verify TLS cert exists on nginx1
docker exec nginx1 ls -la /opt/kafka-ca/nginx1.crt /opt/kafka-ca/nginx1.key

# Test upstream connectivity from nginx1
docker exec nginx1 curl -s http://monitoring1:3000/api/health
docker exec nginx1 curl -s http://kafkaui1:8080/api/clusters
```

**Fix**: If cert is missing, check that `nginx` group was included in `prepare.yml` cert generation play.

---

### Traffic Generator Issues

**Symptoms**: `traffic-generator` service fails or exits; no messages in Kafka topics

```bash
# Check service status and recent logs
docker exec traffic1 systemctl status traffic-generator
docker exec traffic1 journalctl -u traffic-generator -n 50 --no-pager

# Manually test kafka-python is installed
docker exec traffic1 python3 -c "import kafka; print(kafka.__version__)"

# Manually test Kafka connectivity from traffic1
docker exec traffic1 python3 -c "
from kafka import KafkaProducer
p = KafkaProducer(bootstrap_servers=['kafka1:9092'])
print('connected')
p.close()
"

# Check if topics were auto-created by producer
docker exec kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

---

## Filtering Ansible Output

When running Molecule commands, always filter to avoid context window bloat:

```bash
# Show only failures and summary
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario)" -A 15

# Show more context around failures
molecule converge 2>&1 | grep -B 5 -A 25 "fatal:"
```
