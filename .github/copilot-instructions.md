# Copilot Instructions for Kafka Ansible Collection

## Project Overview

This is an Ansible Collection for deploying Apache Kafka clusters with ZooKeeper plus a full Prometheus/Grafana observability stack. The codebase uses Ansible Molecule for testing.

## Project Structure

```
roles/
  common/            # Common system configuration
  java/              # OpenJDK installation
  rootca/            # TLS certificate authority
  zookeeper/         # ZooKeeper cluster deployment
  kafka/             # Kafka broker deployment
  jmx_exporter/     # JMX Prometheus Java agent (Kafka + ZooKeeper metrics)
  nginx/             # Nginx reverse proxy (TLS + basic auth)
extensions/molecule/
  default/           # Primary Molecule scenario
    converge.yml     # Main deployment playbook
    converge/        # Modular task files (kafka-exporter, grafana, traffic)
    verify.yml       # Verification tests
    verify/          # Modular verify task files per component
    files/
      dashboards/    # Grafana dashboard JSON files
      traffic_generator.py  # Python Kafka producer/consumer
  inventory/
    group_vars/all.yml  # All scenario variables
```

## Molecule Test Environment

- **Platform**: Rocky Linux 9 (Docker containers with systemd)
- **Hosts**:
  - `rootca1` (rootca group) — Certificate authority
  - `zk1`, `zk2`, `zk3` (zookeeper group) — ZooKeeper ensemble
  - `kafka1`, `kafka2`, `kafka3` (kafka group) — Kafka brokers
  - `monitoring1` (monitoring group) — Prometheus + Grafana + kafka_exporter + Node Exporter
  - `nginx1` (nginx group) — Nginx reverse proxy (TLS + basic auth)
  - `traffic1` (traffic group) — Python Kafka traffic generator
  - `kafkaui1` (kafkaui group) — Kafbat Kafka UI

## Testing Workflow

**IMPORTANT**: Always run Molecule from the **project root**, NOT from `extensions/molecule`.

### Preferred Workflow

1. Run `molecule converge` to apply changes (preserves infrastructure)
2. If converge succeeds, run `molecule idempotence` to verify idempotency
3. Then run `molecule verify` to run verification tests
4. Keep infrastructure running for manual verification

### Avoid

- `molecule test` - destroys infrastructure after testing
- `molecule destroy` - unless a hard reset is needed

## Output Filtering

Ansible produces verbose output that fills context windows. Always filter:

```bash
# Filter to show only failures and summary
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario)" -A 15
```

## Container Access

**Prefer `docker exec` over `molecule login`** for non-interactive commands:

```bash
# Use docker exec for single commands
docker exec -it zk1 /opt/zookeeper/bin/zkServer.sh status
docker exec -it kafka1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# molecule login requires interactive shell
molecule login -h zk1
```

## Variable Precedence

1. `roles/<role>/defaults/main.yml` - Default values (lowest priority)
2. `roles/<role>/vars/<os_family>.yml` - OS-specific (RedHat.yml, Debian.yml)
3. `roles/<role>/vars/default.yml` - Additional defaults
4. Inventory variables - Can override role defaults
5. Extra vars (`-e`) - Highest priority

## Observability Stack Details

### Metrics Pipeline
```
kafka1-3:7071/metrics   ← JMX Exporter (Kafka brokers)
zk1-3:7072/metrics      ← JMX Exporter (ZooKeeper)
monitoring1:9308/metrics ← kafka_exporter (consumer lag)
all nodes:9100/metrics  ← Node Exporter
         ↓
monitoring1:9090        ← Prometheus scrapes all targets
         ↓
monitoring1:3000        ← Grafana visualizes
         ↓
nginx1:443              ← Nginx reverse proxy
  /           → kafkaui1:8080  (Kafka UI)
  /grafana/   → monitoring1:3000 (Grafana)
```

### Key Ports
| Port | Service | Host |
|------|---------|------|
| 9090 | Prometheus | monitoring1 (published to localhost) |
| 3000 | Grafana | monitoring1 (published to localhost) |
| 443  | Nginx HTTPS | nginx1 (published to localhost) |
| 7071 | JMX Exporter | kafka1-3 |
| 7072 | JMX Exporter | zk1-3 |
| 9308 | kafka_exporter | monitoring1 |
| 9100 | Node Exporter | all Rocky nodes |

### Grafana Access
- **Direct**: `http://localhost:3000` (admin / admin)
- **Via Nginx**: `https://nginx1/grafana/` (admin / admin, self-signed cert)
- **Dashboards**: Kafka Broker Overview, Consumer Lag, ZooKeeper Overview (file-provisioned); Node Exporter Full, Kafka Exporter Overview (Grafana Labs IDs 1860, 7589, 721)

### JMX Exporter
- Version: 1.0.1 (Maven Central)
- JAR: `/opt/jmx-exporter/jmx_prometheus_javaagent.jar`
- Configs: `/opt/jmx-exporter/kafka.yml`, `/opt/jmx-exporter/zookeeper.yml`
- Enabled via `kafka_jmx_exporter_enabled: true` / `zookeeper_jmx_exporter_enabled: true` in `group_vars/all.yml`

### kafka_exporter
- Version: v1.9.0 (danielqsj/kafka_exporter)
- Binary: `/opt/kafka_exporter/kafka_exporter`
- Connects to: `kafka1:9092,kafka2:9092,kafka3:9092`

### Traffic Generator
- Script: `/opt/traffic-generator/traffic_generator.py`
- Topics: `user-events`, `order-processing`, `analytics-data`, `notifications`, `system-logs`
- Consumer groups: `analytics-consumer`, `audit-consumer`, `reporting-consumer`
- Configure via env vars: `KAFKA_BOOTSTRAP_SERVERS`, `PRODUCE_INTERVAL`, `CONSUME_INTERVAL`

## Common Failure Patterns

| Error Pattern | Likely Cause | Fix Location |
|--------------|--------------|--------------|
| `'variable_name' is undefined` | Missing variable | `defaults/main.yml` or `group_vars/all.yml` |
| `conditional check ... failed` | Undefined in `when:` | Define before conditional |
| `No file was found` | Missing template/file | `templates/` or `files/` |
| `handler not found` | Handler name mismatch | Match `notify:` with handler `name:` |
| JMX metrics missing in Prometheus | JMX Exporter JAR not loaded | Check `kafka_jmx_exporter_enabled`, journalctl on kafka/zk node |
| Grafana dashboard blank | Wrong Prometheus job name | Verify job names in Prometheus scrape config match dashboard queries |
| Nginx 502 Bad Gateway | Upstream service not ready | Check Grafana/kafkaui service status |
| kafka_exporter no metrics | Kafka brokers not yet up | kafka_exporter starts after converge; wait or check service logs |
| Traffic generator not producing | kafka-python not installed or Kafka unreachable | Check pip install, verify bootstrap servers |
