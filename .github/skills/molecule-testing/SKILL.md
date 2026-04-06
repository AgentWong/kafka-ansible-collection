---
name: molecule-testing
description: Run Ansible Molecule tests for the Kafka collection. Use when testing Ansible roles, running converge/verify cycles, or troubleshooting test failures.
---

# Molecule Testing for Kafka Ansible Collection

This skill helps run and troubleshoot Ansible Molecule tests for deploying Kafka clusters.

## When to Use This Skill

- Running Molecule test scenarios
- Debugging Ansible playbook failures
- Verifying role changes work correctly
- Testing idempotency of Ansible plays

## Test Environment

| Container | Group | Purpose |
|-----------|-------|---------|
| `rootca1` | rootca | TLS Certificate Authority |
| `zk1`, `zk2`, `zk3` | zookeeper | ZooKeeper ensemble + JMX Exporter (:7072) |
| `kafka1`, `kafka2`, `kafka3` | kafka | Kafka brokers + JMX Exporter (:7071) |
| `monitoring1` | monitoring | Prometheus (:9090) + Grafana (:3000) + kafka_exporter (:9308) + Node Exporter |
| `nginx1` | nginx | Nginx reverse proxy HTTPS (:443) |
| `traffic1` | traffic | Python traffic generator (producer + 3 consumers) |
| `kafkaui1` | kafkaui | Kafbat Kafka UI (:8080) |

**Platform**: Rocky Linux 9 with systemd (Docker), except `kafkaui1` (Kafbat image)

## Preferred Workflow

**IMPORTANT**: Preserve infrastructure between test runs. Only destroy when absolutely necessary.

### Step 1: Converge (Apply Changes)

```bash
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario|changed=)" -A 15
```

This runs the Ansible playbook without destroying infrastructure.

### Step 2: Idempotence (Verify No Changes on Re-run)

Only run if converge succeeds:

```bash
molecule idempotence 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|changed=)" -A 10
```

A successful idempotence test shows `changed=0` for all hosts.

### Step 3: Verify (Run Assertions)

```bash
molecule verify 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|ok=)" -A 10
```

### Keep Infrastructure Running

After the workflow completes, infrastructure remains available for manual verification:
- Access containers via `docker exec`
- Test Kafka/ZooKeeper functionality directly
- Iterate on fixes without full rebuild

## Commands to AVOID

```bash
# DON'T USE - destroys infrastructure
molecule test        # Runs full cycle including destroy
molecule destroy     # Explicitly destroys containers

# Only use destroy if:
# - Containers are corrupted
# - Need a completely fresh start
# - User explicitly requests it
```

## Output Filtering

Ansible generates verbose output. Always filter to preserve context:

```bash
# Standard failure filter
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario)" -A 15

# More context around failures
molecule converge 2>&1 | grep -B 5 -A 25 "fatal:"

# Last 50 lines (quick check)
molecule converge 2>&1 | tail -50
```

## Working Directory

**CRITICAL**: Always run Molecule from the project root, not from `extensions/molecule`:

```bash
# Correct
cd ~/Documents/vscode/kafka-ansible-collection
molecule converge

# Wrong
cd extensions/molecule
molecule converge  # May fail or use wrong paths
```

## Analyzing Failures

### Common Error Patterns

| Pattern | Cause | Fix Location |
|---------|-------|--------------|
| `'variable_name' is undefined` | Missing variable | `roles/<role>/defaults/main.yml` |
| `No file was found when using` | Missing template | `roles/<role>/templates/` |
| `handler not found` | Handler mismatch | `roles/<role>/handlers/main.yml` |
| `conditional check failed` | Variable undefined in `when:` | Define before the task |

### Variable Definition Priority

1. `defaults/main.yml` - Lowest priority defaults
2. `vars/RedHat.yml` or `vars/Debian.yml` - OS-specific
3. `vars/default.yml` - Additional defaults
4. Molecule inventory vars - Test overrides
5. Extra vars (`-e`) - Highest priority

### Debugging Steps

1. **Read the error message** - Note the failing task and file path
2. **Check the role file** - Read the task that failed
3. **Verify variables** - Check `defaults/` and `vars/` directories
4. **Inspect container** - Use `docker exec` to check actual state
5. **Apply fix** - Edit the appropriate file
6. **Re-run converge** - Test the fix

## Container Inspection

Use `docker exec` for non-interactive commands:

```bash
# --- Core cluster ---
docker exec -it kafka1 systemctl status kafka
docker exec -it zk1 systemctl status zookeeper
docker exec -it kafka1 journalctl -u kafka -n 50 --no-pager
docker exec -it kafka1 cat /opt/kafka/config/server.properties

# --- JMX Exporter ---
docker exec -it kafka1 curl -s http://localhost:7071/metrics | head -20
docker exec -it zk1 curl -s http://localhost:7072/metrics | head -20

# --- Monitoring stack ---
docker exec -it monitoring1 systemctl status prometheus grafana-server kafka_exporter
docker exec -it monitoring1 curl -s http://localhost:9090/-/healthy
docker exec -it monitoring1 curl -s 'http://localhost:9090/api/v1/targets' | python3 -m json.tool | grep '"health"'
docker exec -it monitoring1 curl -s http://localhost:3000/api/health
docker exec -it monitoring1 curl -s http://localhost:9308/metrics | grep kafka_brokers

# --- Nginx ---
docker exec -it nginx1 systemctl status nginx
docker exec -it nginx1 nginx -t
curl -k -u admin:admin https://localhost/grafana/api/health

# --- Traffic generator ---
docker exec -it traffic1 systemctl status traffic-generator
docker exec -it traffic1 journalctl -u traffic-generator -n 30 --no-pager
```

## Verify Task Files

Each component has its own verify task file under `extensions/molecule/default/verify/`:

| File | What it checks |
|------|----------------|
| `jmx-exporter-check.yml` | Ports 7071/7072 responding, metrics present |
| `prometheus-check.yml` | Service active, all targets UP via API |
| `grafana-check.yml` | Service active, Prometheus datasource configured |
| `kafka-exporter-check.yml` | Service active, `kafka_brokers` metric present |
| `nginx-check.yml` | Service active, Kafka UI and Grafana accessible via HTTPS |
| `traffic-generator-check.yml` | Service active, topics exist |
| `monitoring-integration.yml` | Prometheus can query JMX, kafka_exporter, node_exporter metrics |
| `summary-display.yml` | Prints all endpoints and credentials |

## Iterative Testing

When fixing issues:

1. Make ONE fix at a time
2. Re-run `molecule converge` (not full test)
3. Check if the specific error is resolved
4. Move to the next error
5. Only run idempotence/verify after all converge errors are fixed
