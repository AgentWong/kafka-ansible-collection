# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

### Added

#### Observability Stack (Prometheus + Grafana + Nginx + Python)

- **`jmx_exporter` role** — Installs JMX Prometheus Java agent (v1.0.1 from Maven Central) on Kafka and ZooKeeper nodes; deploys Kafka and ZooKeeper MBean config YAML files with comprehensive metric patterns
- **`nginx` role** — Installs and configures Nginx reverse proxy with TLS termination (Root CA-signed cert) and HTTP basic auth; routes `/` to Kafka UI and `/grafana/` to Grafana
- **`monitoring1` container** — New Molecule node (Rocky Linux 9) running Prometheus, Grafana, kafka_exporter, and Node Exporter
- **`nginx1` container** — New Molecule node (Rocky Linux 9) running Nginx reverse proxy (HTTPS :443)
- **`traffic1` container** — New Molecule node (Rocky Linux 9) running the Python traffic generator
- **JMX Exporter on Kafka brokers** — Exposes Prometheus metrics at `:7071/metrics`; enabled via `kafka_jmx_exporter_enabled: true`
- **JMX Exporter on ZooKeeper nodes** — Exposes Prometheus metrics at `:7072/metrics`; enabled via `zookeeper_jmx_exporter_enabled: true`
- **Prometheus** (via `prometheus.prometheus.prometheus` role) — Scrapes all cluster targets with 5 configured jobs: `kafka-jmx`, `zookeeper-jmx`, `kafka-exporter`, `node`, `prometheus`
- **Node Exporter** (via `prometheus.prometheus.node_exporter` role) — Deployed on all Rocky Linux nodes; exposes system metrics at `:9100/metrics`
- **kafka_exporter v1.9.0** (danielqsj) — Binary service on `monitoring1`; exposes consumer group lag and broker metrics at `:9308/metrics`
- **Grafana** — Installed from official RPM repository; file-based dashboard and datasource provisioning; Prometheus datasource auto-configured
- **Grafana dashboards** — Three custom file-provisioned JSON dashboards (Kafka Broker Overview, Kafka Consumer Lag, ZooKeeper Overview) plus three imported from Grafana Labs by ID (7589 Kafka Exporter Overview, 1860 Node Exporter Full, 721 Kafka Overview JMX)
- **Prometheus alert rules** — Four alerts: `KafkaBrokerDown`, `UnderReplicatedPartitions`, `ZooKeeperDown`, `ConsumerGroupLag`
- **Python traffic generator** (`extensions/molecule/files/traffic_generator.py`) — Multi-threaded producer and three consumer groups with deliberate variable delays to generate visible consumer lag; configurable via environment variables
- **Modular converge task files** under `extensions/molecule/default/converge/`: `kafka-exporter-setup.yml`, `grafana-setup.yml`, `grafana-dashboards.yml`, `traffic-generator.yml`
- **Modular verify task files** under `extensions/molecule/default/verify/`: `jmx-exporter-check.yml`, `prometheus-check.yml`, `grafana-check.yml`, `kafka-exporter-check.yml`, `nginx-check.yml`, `traffic-generator-check.yml`, `monitoring-integration.yml`, `summary-display.yml`
- **`prometheus.prometheus >= 0.29.0`** and **`community.grafana >= 2.0.0`** added to `requirements.yml`
- New variables in `group_vars/all.yml`: `jmx_exporter_version`, `jmx_exporter_kafka_port`, `jmx_exporter_zookeeper_port`, `kafka_jmx_exporter_enabled`, `zookeeper_jmx_exporter_enabled`, `grafana_admin_password`, `kafka_exporter_version`, `nginx_basic_auth_user`, `nginx_basic_auth_password`, `traffic_bootstrap_servers`, `traffic_produce_interval`, `traffic_consume_interval`
- Copilot instructions, molecule prompt, and skills updated to cover all new components
- New `observability-stack` Copilot skill with architecture reference, health check commands, and extension guide

#### Documentation
- `docs/ARCHITECTURE.md` — Expanded with full 11-node topology, metrics pipeline diagram, observability component details, alert rules table, traffic generator topics/consumer groups table, updated resource requirements
- `README.md` — Updated features list, architecture diagram, node table, quick start access URLs table, observability stack section (metrics pipeline, dashboards, alerts, traffic generator), updated roles table and repository structure

### Changed
- `extensions/molecule/config.yml` — Added `monitoring1`, `nginx1`, and `traffic1` container platforms; cluster grows from 8 to 11 nodes
- `extensions/molecule/default/converge.yml` — Added plays for JMX Exporter, Node Exporter, Prometheus, kafka_exporter, Grafana, Nginx, and traffic generator
- `extensions/molecule/default/verify.yml` — Replaced single summary block with modular per-component verification plays
- `extensions/molecule/default/prepare.yml` — Extended TLS certificate generation to include `nginx` group
- `roles/kafka/templates/kafka-env.sh.j2` — Added conditional JMX Exporter javaagent flag
- `roles/zookeeper/templates/java.env.j2` — Added conditional JMX Exporter javaagent flag
- `roles/kafka/defaults/main.yml` — Added `kafka_jmx_exporter_enabled: false` default
- `roles/zookeeper/defaults/main.yml` — Added `zookeeper_jmx_exporter_enabled: false` default

### Fixed

#### ZooKeeper Dashboard Metrics (Empty Panels)

- **`zookeeper_avglatency` → `zookeeper_avgrequestlatency`** — Dashboard query corrected to match the metric name actually emitted by JMX Exporter 1.0.x. The `AvgRequestLatency` attribute is captured from the `Leader`/`Follower` sub-bean by the catch-all rule, which lowercases the attribute to `avgrequestlatency`; the earlier specific rule targeting the bare replica bean never matched.
- **`zookeeper_znodecount`, `zookeeper_watchcount`, `zookeeper_pendingsyncs`** — These attributes do not exist as JMX MBean attributes in ZooKeeper 3.8+; they are only available via the `mntr` four-letter-words command. Fixed by introducing a `mntr`-based textfile exporter (see below).
- **ZooKeeper mntr textfile exporter** — New shell script (`roles/zookeeper/templates/zookeeper-mntr-exporter.sh.j2`) that reads `mntr` output and writes Prometheus-format metrics to `/var/lib/node_exporter/zookeeper.prom`, picked up by node_exporter's existing textfile collector. Deployed as a systemd oneshot service (`zookeeper-mntr-exporter.service`) triggered every 60 s by a systemd timer (`zookeeper-mntr-exporter.timer`). Emits: `zookeeper_mntr_znode_count`, `zookeeper_mntr_watch_count`, `zookeeper_mntr_pending_syncs`, `zookeeper_mntr_avg_latency`, `zookeeper_mntr_num_alive_connections`, `zookeeper_mntr_outstanding_requests`.
- **ZooKeeper Overview dashboard** (`extensions/molecule/files/dashboards/zookeeper-overview.json`) — Updated panel queries: Average Latency uses `zookeeper_avgrequestlatency`; ZNode Count, Watch Count, and Pending Syncs use the new `zookeeper_mntr_*` metrics.
- **`roles/zookeeper/defaults/main.yml`** — Added `zookeeper_mntr_exporter_enabled: false`, `zookeeper_mntr_textfile_dir`, and `zookeeper_mntr_exporter_script` defaults.
- **`roles/zookeeper/tasks/configure.yml`** — Added tasks to deploy mntr exporter script, systemd service and timer units, and run an immediate seed scrape after ZooKeeper starts.
- **`extensions/molecule/inventory/group_vars/all.yml`** — Added `zookeeper_mntr_exporter_enabled: true` for molecule testing.

### Security
- TLS encryption for all Kafka and ZooKeeper communications
- Nginx TLS termination with Root CA-signed certificate
- HTTP basic authentication on all Nginx-proxied endpoints
