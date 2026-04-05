---
name: observability-stack
description: Verify, debug, and extend the Prometheus/Grafana/Nginx observability stack added to the Kafka collection. Use when checking monitoring health, Prometheus targets, Grafana dashboards, Nginx proxy, JMX metrics, kafka_exporter, or the Python traffic generator.
---

# Observability Stack for Kafka Ansible Collection

This skill covers the full Prometheus + Grafana + Nginx + Python observability stack deployed alongside the Kafka cluster.

## When to Use This Skill

- Checking if Prometheus targets are UP
- Debugging Grafana dashboard data issues
- Verifying JMX Exporter metrics from Kafka/ZooKeeper nodes
- Troubleshooting Nginx reverse proxy routing
- Inspecting traffic generator output and consumer lag

## Architecture

```
JMX Exporter agents (java agent loaded at JVM startup)
  kafka1-3:7071   ←  Kafka broker JMX metrics
  zk1-3:7072      ←  ZooKeeper JMX metrics

kafka_exporter (binary service on monitoring1)
  monitoring1:9308  ←  Consumer group lag, broker count, topic metrics

Node Exporter (binary service on all Rocky nodes)
  all nodes:9100    ←  CPU, memory, disk, network

Prometheus (monitoring1:9090)
  scrapes all targets above on 15s interval

Grafana (monitoring1:3000)
  datasource: Prometheus (http://localhost:9090)
  dashboards: file-provisioned + Grafana Labs IDs 7589, 1860, 721

Nginx (nginx1:443)
  /           → kafkaui1:8080  (Kafka UI, no sub-path issues)
  /grafana/   → monitoring1:3000 (serve_from_sub_path=true in grafana.ini)
  auth: basic auth (admin/admin), self-signed TLS cert
```

## Quick Health Check

```bash
# All-in-one status
docker exec monitoring1 systemctl status prometheus grafana-server kafka_exporter --no-pager
docker exec nginx1 systemctl status nginx --no-pager
docker exec traffic1 systemctl status traffic-generator --no-pager

# Prometheus targets summary
docker exec monitoring1 curl -s 'http://localhost:9090/api/v1/targets' \
  | python3 -c "
import json,sys
data = json.load(sys.stdin)
for t in data['data']['activeTargets']:
    print(f\"{t['health']:5}  {t['labels']['job']:20}  {t['scrapeUrl']}\")
"

# Grafana health
docker exec monitoring1 curl -s http://localhost:3000/api/health

# kafka_exporter broker count
docker exec monitoring1 curl -s http://localhost:9308/metrics | grep '^kafka_brokers'

# Nginx routing
curl -sk -u admin:admin https://localhost/grafana/api/health
curl -sk -u admin:admin https://localhost/ -o /dev/null -w "KafkaUI HTTP: %{http_code}\n"
```

## Component Reference

### JMX Exporter

- **Version**: 1.0.1 (Maven Central)
- **JAR path**: `/opt/jmx-exporter/jmx_prometheus_javaagent.jar`
- **Kafka config**: `/opt/jmx-exporter/kafka.yml`
- **ZooKeeper config**: `/opt/jmx-exporter/zookeeper.yml`
- **Enable flag**: `kafka_jmx_exporter_enabled: true` / `zookeeper_jmx_exporter_enabled: true` in `group_vars/all.yml`
- **Scrape URL**: `http://<host>:<port>/metrics` (NOT root `/` — changed in 1.x)

```bash
# Check JMX agent is in Kafka JVM args
docker exec kafka1 jps -v | grep -o 'jmx_prometheus[^ ]*'

# Sample metrics
docker exec kafka1 curl -s http://localhost:7071/metrics | grep kafka_server_brokertopicmetrics | head -5
docker exec zk1 curl -s http://localhost:7072/metrics | grep zookeeper | head -5
```

### Prometheus

- **Config**: `/etc/prometheus/prometheus.yml` (managed by `prometheus.prometheus.prometheus` role)
- **Alert rules**: inline in `converge.yml` (`prometheus_alert_rules` var)
- **Data dir**: `/var/lib/prometheus/`

```bash
# Reload config without restart
docker exec monitoring1 curl -s -X POST http://localhost:9090/-/reload

# Query a metric
docker exec monitoring1 curl -sg 'http://localhost:9090/api/v1/query?query=kafka_brokers' \
  | python3 -m json.tool

# Check alert rules
docker exec monitoring1 curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool
```

### Grafana

- **Config**: `/etc/grafana/grafana.ini`
- **Dashboards**: `/var/lib/grafana/dashboards/` (file-provisioned)
- **Provisioning**: `/etc/grafana/provisioning/`
- **Credentials**: admin / admin (set via `grafana_admin_password` in `group_vars/all.yml`)

```bash
# List provisioned dashboards
docker exec monitoring1 ls /var/lib/grafana/dashboards/

# Check datasource via API
docker exec monitoring1 curl -s -u admin:admin http://localhost:3000/api/datasources

# Reload dashboards (triggers re-scan of provisioning dir)
docker exec monitoring1 curl -s -u admin:admin -X POST http://localhost:3000/api/admin/provisioning/dashboards/reload
```

**Dashboard inventory**:

| Dashboard | Source | Prometheus Job |
|-----------|--------|----------------|
| Kafka Broker Overview | File-provisioned JSON | `kafka-jmx` |
| Kafka Consumer Lag | File-provisioned JSON | `kafka-exporter` |
| ZooKeeper Overview | File-provisioned JSON | `zookeeper-jmx` |
| Kafka Exporter Overview | Grafana Labs ID 7589 | `kafka-exporter` |
| Node Exporter Full | Grafana Labs ID 1860 | `node` |
| Kafka Overview (JMX) | Grafana Labs ID 721 | `kafka-jmx` (job must be `kafka`) |

> **Note**: Dashboard ID 721 expects the Prometheus job to be named `kafka`. Currently the job is `kafka-jmx`. Either rename the scrape job or use dashboard ID 7589 for kafka_exporter metrics.

### kafka_exporter

- **Version**: v1.9.0 (danielqsj/kafka_exporter)
- **Binary**: `/opt/kafka_exporter/kafka_exporter`
- **Service**: `kafka_exporter` (systemd)
- **Metrics port**: 9308
- **Connects to**: `kafka1:9092,kafka2:9092,kafka3:9092`

```bash
docker exec monitoring1 systemctl status kafka_exporter
docker exec monitoring1 curl -s http://localhost:9308/metrics | grep -E '^(kafka_brokers|kafka_topic_partitions|kafka_consumergroup_lag)'
```

### Nginx Reverse Proxy

- **Config**: `/etc/nginx/nginx.conf` (managed by `nginx` role template)
- **TLS cert**: `/opt/kafka-ca/nginx1.crt` and `nginx1.key` (signed by Root CA)
- **Basic auth**: `/etc/nginx/.htpasswd` (admin/admin)
- **Routes**: `/` → kafkaui1:8080, `/grafana/` → monitoring1:3000
- **Published port**: 443 (localhost)

```bash
docker exec nginx1 nginx -t
docker exec nginx1 cat /etc/nginx/nginx.conf

# Test routes
curl -sk -u admin:admin https://localhost/ -D - | head -5
curl -sk -u admin:admin https://localhost/grafana/api/health
```

### Traffic Generator

- **Script**: `/opt/traffic-generator/traffic_generator.py`
- **Service**: `traffic-generator` (systemd)
- **Topics produced**: `user-events`, `order-processing`, `analytics-data`, `notifications`, `system-logs`
- **Consumer groups**: `analytics-consumer` (1s delay), `audit-consumer` (8s delay), `reporting-consumer` (15s delay)
- **Config**: env vars in systemd unit (`KAFKA_BOOTSTRAP_SERVERS`, `PRODUCE_INTERVAL`, `CONSUME_INTERVAL`)

```bash
docker exec traffic1 systemctl status traffic-generator
docker exec traffic1 journalctl -u traffic-generator -f --no-pager

# Check consumer group lag (should be non-zero due to intentional delays)
docker exec kafka1 /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --all-groups 2>/dev/null | head -30
```

## Extending the Stack

### Adding a new Grafana dashboard

1. Create `extensions/molecule/files/dashboards/<name>.json` with `"uid": "<unique-uid>"` set
2. Re-run `molecule converge` — Grafana auto-reloads file-provisioned dashboards within 30s
3. Or trigger reload: `docker exec monitoring1 curl -s -u admin:admin -X POST http://localhost:3000/api/admin/provisioning/dashboards/reload`

### Adding a new Prometheus scrape target

1. Add to `prometheus_scrape_configs` in the Prometheus play in `converge.yml`
2. Re-run `molecule converge` — Prometheus config is regenerated and reloaded

### Adding a new alert rule

1. Add to `prometheus_alert_rules` list in `converge.yml`
2. Re-run `molecule converge`
3. Verify: `docker exec monitoring1 curl -s http://localhost:9090/api/v1/rules`
