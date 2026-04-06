---
agent: agent
description: Run complete Molecule test workflow with autonomous fix-and-retry loop until all tests pass
tools:
  [execute, read, agent, edit, search, web, ms-azuretools.vscode-containers/containerToolsConfig, todo]
---

# Molecule Test Workflow (Autonomous)

Run the complete Molecule testing workflow with automatic error fixing. Continue retrying until all tests pass.

## Autonomous Operation

**CRITICAL**: Do NOT stop and ask the user for help on failures. Diagnose issues, implement fixes, and re-run tests automatically. Only escalate to the user after **20+ failed fix attempts** or truly catastrophic failures (e.g., Docker daemon down, network unavailable, permissions issues that require sudo).

## Workflow Overview

```
┌─────────────────────────────────────────────────────────┐
│  1. Run molecule converge                               │
│  2. If FAILED → diagnose, fix, goto 1                   │
│  3. Run molecule idempotence                            │
│  4. If FAILED → diagnose, fix, goto 1                   │
│  5. Run molecule verify                                 │
│  6. If FAILED → diagnose, fix, goto 1                   │
│  7. Run molecule converge -s demo (populate demo data)  │
│  8. If FAILED → diagnose, fix, goto 7                   │
│  9. Run molecule verify -s demo                         │
│ 10. If FAILED → diagnose, fix, goto 7                   │
│ 11. SUCCESS → Report completion, keep infra running     │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: Converge

```bash
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario|ok=)" -A 15
```

## Phase 2: Idempotence

```bash
molecule idempotence 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|changed=)" -A 10
```

**Success criteria**: All hosts show `changed=0`

## Phase 3: Verify

```bash
molecule verify 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|ok=|TASK)" -A 10
```

## Phase 4: Demo Data

After the default scenario passes, populate the Kafka cluster with demo data using the `demo` scenario:

```bash
molecule converge -s demo 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|ok=|TASK)" -A 10
```

Then verify the demo data was created correctly:

```bash
molecule verify -s demo 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|ok=|TASK)" -A 10
```

**Success criteria**: 5 demo topics created, ~575 messages produced, 3 consumer groups started, Kafka UI shows all topics at `http://localhost:8080/ui/clusters/kafka-cluster`

If either command fails, diagnose and fix, then re-run from `molecule converge -s demo` (no need to re-run the default scenario unless the fix touches default scenario files).

## Autonomous Fix Loop

When ANY phase fails:

1. **Analyze the error** - Identify the failing task, role, and root cause
2. **Read relevant files** - Check the task file, variable definitions, templates
3. **Implement the fix** - Edit the appropriate file(s)
4. **Re-run from Phase 1** - Always restart from converge after fixes
5. **Track attempts** - Keep count of fix attempts per issue

### Diagnostic Commands (use as needed)

```bash
# --- Core cluster ---
docker exec -it zk1 systemctl status zookeeper
docker exec -it kafka1 systemctl status kafka
docker exec -it zk1 journalctl -u zookeeper -n 100 --no-pager
docker exec -it kafka1 journalctl -u kafka -n 100 --no-pager
docker exec -it zk1 /opt/zookeeper/bin/zkServer.sh status
docker exec -it kafka1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
docker exec -it kafka1 cat /opt/kafka/config/server.properties

# --- JMX Exporter ---
# Verify JMX agent loaded (look for "jmx_prometheus_javaagent" in process args)
docker exec -it kafka1 jps -v | grep jmx
docker exec -it kafka1 curl -s http://localhost:7071/metrics | head -20
docker exec -it zk1 curl -s http://localhost:7072/metrics | head -20

# --- Prometheus ---
docker exec -it monitoring1 systemctl status prometheus
docker exec -it monitoring1 journalctl -u prometheus -n 50 --no-pager
docker exec -it monitoring1 curl -s http://localhost:9090/-/healthy
# Check all targets UP
docker exec -it monitoring1 curl -s 'http://localhost:9090/api/v1/targets' | python3 -m json.tool | grep -E '"health"|"job"|"scrapeUrl"'

# --- Grafana ---
docker exec -it monitoring1 systemctl status grafana-server
docker exec -it monitoring1 journalctl -u grafana-server -n 50 --no-pager
docker exec -it monitoring1 curl -s http://localhost:3000/api/health

# --- kafka_exporter ---
docker exec -it monitoring1 systemctl status kafka_exporter
docker exec -it monitoring1 journalctl -u kafka_exporter -n 50 --no-pager
docker exec -it monitoring1 curl -s http://localhost:9308/metrics | grep kafka_brokers

# --- Nginx ---
docker exec -it nginx1 systemctl status nginx
docker exec -it nginx1 journalctl -u nginx -n 50 --no-pager
docker exec -it nginx1 nginx -t
curl -k -u admin:admin https://localhost/grafana/api/health
curl -k -u admin:admin https://localhost/ -o /dev/null -w "%{http_code}"

# --- Traffic Generator ---
docker exec -it traffic1 systemctl status traffic-generator
docker exec -it traffic1 journalctl -u traffic-generator -n 50 --no-pager
docker exec -it kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
docker exec -it kafka1 /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

### Common Fixes

| Error Pattern | Likely Fix |
|---------------|------------|
| `'variable' is undefined` | Add to `roles/<role>/defaults/main.yml` or `group_vars/all.yml` |
| `No file was found` | Create missing template in `roles/<role>/templates/` |
| `handler not found` | Match `notify:` name with handler `name:` in `handlers/main.yml` |
| `conditional check failed` | Ensure variable is defined before the `when:` clause |
| Service won't start | Check logs with `journalctl`, fix config templates |
| `changed != 0` in idempotence | Make task conditional or use `creates:`/`removes:` |
| JMX metrics missing in Prometheus | Verify `kafka_jmx_exporter_enabled: true` in `group_vars/all.yml`; check JMX agent in `jps -v` output |
| Prometheus target not UP | Check firewall/container network; verify port is bound with `ss -tlnp` |
| Grafana blank dashboards | Wrong job name in query; check Prometheus job names match dashboard `job=` label filters |
| Nginx 502 on `/grafana/` | Grafana not yet started; check `grafana-server` service status on monitoring1 |
| kafka_exporter exits immediately | Kafka brokers not yet ready; kafka_exporter needs brokers reachable at startup |
| Traffic generator fails to start | kafka-python not installed (`pip3 install kafka-python`); check bootstrap servers reachable |

## Context Management

If context window becomes a concern, use `runSubagent` to spawn isolated fix attempts:

```
Subagent task: "Fix the undefined variable 'kafka_broker_id' error in roles/kafka/tasks/main.yml.
Read the error context, implement a fix, and report what was changed."
```

This keeps the orchestrator aware of attempt counts while giving subagents clean context.

## Escalation Criteria

Only ask the user for help if:

- **20+ fix attempts** have failed for the same issue
- **Infrastructure is broken** (Docker not running, can't create containers)
- **External dependencies** missing (network issues, missing packages that can't be installed)
- **Permissions issues** requiring sudo or user intervention
- **Ambiguous requirements** where multiple valid approaches exist and user preference is needed

## Working Directory

Always run from **project root**: `{workspace}`

## Success Criteria

The workflow is complete when:
- `molecule converge` shows `failed=0`
- `molecule idempotence` shows `changed=0` for all hosts
- `molecule verify` passes all assertions
- `molecule converge -s demo` shows `failed=0` (5 topics, ~575 messages, 3 consumer groups)
- `molecule verify -s demo` passes all assertions
- Infrastructure remains running for manual verification
- Kafka UI at `http://localhost:8080/ui/clusters/kafka-cluster` shows demo topics and consumer groups

### Observability Stack Verification Checklist
- `http://localhost:9090` — Prometheus UI accessible, all targets show `UP`
  - Targets: `kafka-jmx` (3), `zookeeper-jmx` (3), `kafka-exporter` (1), `node` (9), `prometheus` (1)
- `http://localhost:3000` — Grafana accessible (admin/admin), Prometheus datasource connected
  - Dashboards loaded: Kafka Broker Overview, Consumer Lag, ZooKeeper Overview, Node Exporter Full, Kafka Exporter Overview
- `https://localhost/` — Nginx proxying Kafka UI (basic auth: admin/admin, accept self-signed cert)
- `https://localhost/grafana/api/health` — Grafana accessible via Nginx sub-path
- `traffic-generator` service running on `traffic1` — topics visible in Kafka UI

## Final Report

On success, provide a summary:
- Number of fix iterations required
- Key issues encountered and how they were resolved
- Any warnings or recommendations for future improvements

## Rules

- **NEVER** run `molecule destroy` or `molecule test` unless explicitly requested
- **NEVER** ask the user for help before 20 fix attempts
- **ALWAYS** restart from Phase 1 (converge) after any fix
- **ALWAYS** filter output with grep to preserve context
- **ALWAYS** keep infrastructure running after completion
- Use `docker exec` for container inspection, not `molecule login`
