# Observability Stack Documentation

## Overview

This collection deploys a complete observability stack alongside the Kafka cluster. The goal is to answer the question: *"Is my Kafka cluster healthy, and what is it doing right now?"*

The stack is composed of four pieces:

| Component | What it does |
|---|---|
| **Prometheus** | Collects and stores metrics from all nodes |
| **Grafana** | Visualizes those metrics in dashboards |
| **Exporters** | Translate Kafka/ZooKeeper internals into a format Prometheus understands |
| **Nginx** | Provides a single, secured HTTPS entry point to Grafana and Kafka UI |

---

## High-Level Data Flow

```
Kafka Brokers  ──► JMX Exporter (:7071) ──────────────────────────────┐
ZooKeeper      ──► JMX Exporter (:7072) ──────────────────────────────┤
ZooKeeper      ──► mntr script → Node Exporter textfile (:9100) ──────┤──► Prometheus ──► Grafana
All Nodes      ──► Node Exporter (:9100) ──────────────────────────────┤       :9090        :3000
Kafka Brokers  ──► kafka_exporter (:9308) ─────────────────────────────┘
```

Prometheus visits each exporter on a schedule (scrapes), collects the latest metrics, and stores them with a timestamp. Grafana then queries Prometheus and renders the results as graphs and tables.

---

## Metric Collection: The Exporters

### Why Exporters?

Prometheus expects metrics to be available at an HTTP endpoint in a specific text format. Kafka and ZooKeeper do not natively expose metrics this way — they use JMX (Java Management Extensions), an internal Java monitoring interface. Exporters act as translators.

### 1. JMX Exporter (Kafka and ZooKeeper)

**What it is:** A small Java agent (a `.jar` file) that attaches directly to the Kafka or ZooKeeper JVM process. It reads JMX metrics from inside the process and serves them over HTTP.

**How it is deployed:**

The agent is injected via a JVM flag in the service startup script. For Kafka:

```bash
# roles/kafka/templates/kafka-env.sh.j2
KAFKA_OPTS="-javaagent:/opt/jmx-exporter/jmx_prometheus_javaagent.jar=7071:/opt/jmx-exporter/kafka.yml"
```

For ZooKeeper, the same pattern runs on port 7072. The YAML file referenced (`kafka.yml`, `zookeeper.yml`) is a filter list that controls which JMX attributes to expose and how to name them in Prometheus.

**What Kafka JMX metrics are collected:**

| Category | Examples |
|---|---|
| Throughput | `BytesInPerSec`, `BytesOutPerSec`, `MessagesInPerSec` per topic |
| Replication health | `UnderReplicatedPartitions`, `ISRShrinks`, `ISRExpands` |
| Cluster control | `ActiveControllerCount`, `LeaderCount`, `PartitionCount` |
| Request latency | Per request type (Produce, Fetch, etc.) with percentiles |
| JVM health | Garbage collection time/count, heap memory usage |

**What ZooKeeper JMX metrics are collected:**

| Category | Examples |
|---|---|
| Latency | `AvgLatency`, `MinLatency`, `MaxLatency` |
| Client activity | `NumAliveConnections`, `OutstandingRequests` |
| Data tree | `ZnodeCount`, `WatchCount` |
| JVM health | GC and memory metrics |

### 2. ZooKeeper mntr Textfile Exporter

ZooKeeper exposes a lightweight diagnostic command called `mntr` (short for "monitor"). This is one of ZooKeeper's [four-letter words](https://zookeeper.apache.org/doc/current/zookeeperAdmin.html#sc_4lw) — simple text commands you can send over a raw TCP connection.

**The problem:** Node Exporter (the host-level metrics collector) cannot call ZooKeeper directly. The solution is a *textfile collector*: a shell script runs on a schedule, queries ZooKeeper, formats the output as Prometheus metrics, and writes them to a `.prom` file. Node Exporter reads that file and serves its contents as if they were its own.

**How it works:**

```
[systemd timer] every 30s
        │
        ▼
[zookeeper-mntr-exporter.sh]
        │  echo "mntr" | nc localhost 2181
        │  parse output
        ▼
[/var/lib/node_exporter/zookeeper.prom]   ← static file on disk
        │
        ▼
[Node Exporter :9100]  ← Prometheus scrapes this
```

**Metrics produced:**

| Metric | Description |
|---|---|
| `zookeeper_mntr_znode_count` | Total number of znodes (data nodes) in the tree |
| `zookeeper_mntr_watch_count` | Active watches registered by clients |
| `zookeeper_mntr_pending_syncs` | Sync operations waiting (follower replication backlog) |
| `zookeeper_mntr_avg_latency` | Average request processing time in milliseconds |
| `zookeeper_mntr_num_alive_connections` | Number of connected clients |
| `zookeeper_mntr_outstanding_requests` | Requests queued but not yet processed |

This approach is useful for metrics that do not come through JMX or where polling via a script is simpler than running a full exporter process.

### 3. kafka_exporter

**What it is:** A standalone binary (not a Java agent) that connects to Kafka as a client and collects consumer group metrics. It runs on `monitoring1` on port 9308.

**Why a separate exporter?** Consumer group lag is not exposed via JMX. It is calculated by comparing how far a consumer group has read versus how many messages have been produced. `kafka_exporter` uses the Kafka admin API to calculate this and exposes it as:

- `kafka_consumer_group_lag` — offset difference per consumer group, topic, and partition
- `kafka_topic_partition_current_offset` — latest produced offset
- `kafka_consumer_group_current_offset` — last committed consumer offset

### 4. Node Exporter

A standard Prometheus component that runs on every node (:9100). It reports host-level metrics:

- CPU usage per core
- Memory and swap utilization
- Disk I/O and filesystem usage
- Network traffic per interface

This provides the infrastructure view alongside the application metrics from JMX.

---

## Prometheus: Collecting and Storing Metrics

### What Prometheus Does

Prometheus is a *pull-based* monitoring system. Rather than exporters sending data to a central server, Prometheus reaches out to each exporter on a regular interval (called a *scrape*) and records whatever metrics are available at that moment. Each data point is stored with a timestamp, building a time-series database.

### Scrape Configuration

Prometheus is configured with five scrape jobs:

```yaml
scrape_configs:
  - job_name: kafka-jmx
    static_configs:
      - targets: [kafka1:7071, kafka2:7071, kafka3:7071]

  - job_name: zookeeper-jmx
    static_configs:
      - targets: [zk1:7072, zk2:7072, zk3:7072]

  - job_name: kafka-exporter
    static_configs:
      - targets: [localhost:9308]

  - job_name: node
    static_configs:
      - targets: [kafka1:9100, kafka2:9100, kafka3:9100,
                  zk1:9100, zk2:9100, zk3:9100,
                  monitoring1:9100]

  - job_name: prometheus
    static_configs:
      - targets: [localhost:9090]   # Prometheus monitors itself
```

Each job maps to a set of targets (host:port pairs). Prometheus records which job a metric came from, so you can query "all Kafka broker metrics" or "all node metrics" by filtering on the `job` label.

### Alert Rules

Prometheus evaluates alert rules continuously against stored data. Alerts are defined alongside the scrape config:

| Alert | Condition | Wait |
|---|---|---|
| `KafkaBrokerDown` | JMX endpoint unreachable | 1 minute |
| `UnderReplicatedPartitions` | Count > 0 | 2 minutes |
| `ZooKeeperDown` | ZK JMX endpoint unreachable | 1 minute |
| `ConsumerGroupLag` | Total lag > 1000 messages | 5 minutes |

The wait period ("for") prevents alerts from firing on momentary blips. An alert only fires if the condition is continuously true for the specified duration.

### Where Prometheus Runs

Prometheus runs on `monitoring1` at port 9090. It is accessible directly during development and also reachable by Grafana (which runs on the same host) at `http://localhost:9090`.

---

## Grafana: Visualizing the Metrics

### How Grafana Connects to Prometheus

Grafana does not collect metrics — it only queries and displays them. The connection to Prometheus is defined as a *datasource*, which is provisioned automatically by Ansible:

```yaml
# /etc/grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://localhost:9090
    access: proxy
    isDefault: true
```

`access: proxy` means Grafana's server process makes queries to Prometheus, not the user's browser. This keeps Prometheus off the public network.

### Dashboard Provisioning

Dashboards are stored as JSON files and deployed to `/var/lib/grafana/dashboards/`. A provisioning config tells Grafana where to look:

```yaml
# /etc/grafana/provisioning/dashboards/kafka-dashboards.yml
providers:
  - name: kafka
    folder: Kafka
    type: file
    options:
      path: /var/lib/grafana/dashboards/
    updateIntervalSeconds: 30
    disableDeletion: true
    allowUiUpdates: false
```

This means:
- Dashboards are loaded from disk automatically at startup and every 30 seconds
- Dashboards cannot be deleted through the Grafana UI
- Manual edits in the UI are not saved back to disk (the JSON file is the source of truth)

This pattern is called *dashboard-as-code*. It ensures dashboards are version-controlled and redeploy identically every time.

### Custom Dashboards

Three custom dashboards are deployed with the collection:

**kafka-broker-overview**: The primary broker health view
- Active controller count (should always be exactly 1)
- Messages in/out per second per topic
- Network request latency by request type
- Request handler thread idle percentage (low % = broker is under load)
- Under-replicated partitions (should be 0 in a healthy cluster)

**zookeeper-overview**: ZooKeeper ensemble health
- Outstanding requests over time (spikes indicate ZooKeeper stress)
- Average request latency in milliseconds
- Number of connected clients
- Total znode count

**kafka-consumer-lag**: Consumer group health
- Total lag stat panel with color thresholds (green < 100, yellow < 1000, red > 1000)
- Per-group and per-topic lag over time
- Messages in vs. messages consumed rates

Two additional dashboards are imported from Grafana Labs at deploy time (community dashboards identified by a numeric ID):
- **Kafka Exporter Overview** (ID 7589): Consumer group lag detail
- **Node Exporter Full** (ID 1860): Complete host metrics for all nodes

### Sub-Path Routing

Grafana is configured to serve from `/grafana/` rather than the root path:

```ini
# /etc/grafana/grafana.ini
[server]
root_url = https://nginx1/grafana/
serve_from_sub_path = true
```

This allows Nginx to host both Grafana and Kafka UI under the same HTTPS port without port conflicts.

---

## Nginx: Securing Access

Nginx runs on `nginx1` as a reverse proxy. Users connect to it; Nginx forwards requests internally.

```
Browser ──HTTPS:443──► Nginx (nginx1)
                           │
                           ├── /grafana/ ──► monitoring1:3000 (Grafana)
                           │
                           └── /         ──► kafkaui1:8080   (Kafka UI)
```

**Security features:**
- HTTP (port 80) redirects to HTTPS (port 443)
- TLS certificates issued by the collection's own Root CA
- Basic authentication (username/password prompt) on all routes
- TLS 1.2/1.3 only, with strong cipher suites

**Why a reverse proxy?**

Without Nginx, Grafana and Kafka UI would each require their own port (3000, 8080) and would not have TLS. Nginx consolidates them behind a single HTTPS port with authentication, which is the standard pattern for exposing internal services.

---

## Traffic Generator

The Python traffic generator runs on `traffic1` as a systemd service. It serves one purpose: give the dashboards something real to display.

**Three consumer groups with intentional lag:**

| Group | Processing delay | Expected lag |
|---|---|---|
| `analytics-consumer` | 1 second | Low |
| `audit-consumer` | 8 seconds | Medium |
| `reporting-consumer` | 15 seconds | High (visible on dashboards) |

The lag is artificial — created by `time.sleep()` inside each consumer — but the metrics it generates are real Prometheus data pulled from an actual Kafka cluster. This makes the dashboards demonstrate consumer lag alerting as intended rather than showing flat zero lines.

Topics produced to: `user-events`, `order-processing`, `analytics-data`, `notifications`, `system-logs`.

---

## Deployment Order

The observability stack is deployed after the core cluster is running:

```
1. Common (all nodes)         - packages, users, system limits
2. Java (JVM nodes)           - OpenJDK 17
3. JMX Exporter (K + ZK)     - agent JAR + config
4. ZooKeeper                  - cluster formation
5. Kafka                      - broker startup
6. Node Exporter (all)        - host metrics
7. Prometheus                 - scrape config + alert rules
8. kafka_exporter             - consumer lag metrics
9. Grafana                    - datasource + dashboard provisioning
10. Nginx                     - reverse proxy + TLS + basic auth
11. Traffic Generator         - synthetic load
```

Steps 7–11 only run on `monitoring1` or `nginx1`/`traffic1`; they have no impact on the Kafka or ZooKeeper services.

---

## Accessing the Stack

After `molecule converge`:

| Interface | URL | Credentials |
|---|---|---|
| Kafka UI + Grafana (via Nginx) | `https://localhost/` and `https://localhost/grafana/` | admin / admin |
| Prometheus (direct) | `http://localhost:9090` | none |
| Grafana (direct, no auth) | `http://localhost:3000` | admin / admin |
| Kafka UI (direct) | `http://localhost:8080` | none |

The Nginx-fronted URLs are the production-like access path. The direct ports are exposed in the Molecule Docker config for debugging.

---

