# Copilot Instructions for Kafka Ansible Collection

## Project Overview

This is an Ansible Collection for deploying Apache Kafka clusters with ZooKeeper. The codebase uses Ansible Molecule for testing.

## Project Structure

```
roles/
  common/            # Common system configuration
  java/              # OpenJDK installation
  rootca/            # TLS certificate authority
  zookeeper/         # ZooKeeper cluster deployment
  kafka/             # Kafka broker deployment
extensions/molecule/
  default/           # Primary Molecule scenario
    molecule.yml     # Scenario configuration (Docker-based)
    converge.yml     # Main deployment playbook
    verify.yml       # Verification tests
```

## Molecule Test Environment

- **Platform**: Rocky Linux 9 (Docker containers with systemd)
- **Hosts**:
  - `rootca1` (rootca group) - Certificate authority
  - `zk1`, `zk2`, `zk3` (zookeeper group) - ZooKeeper ensemble
  - `kafka1`, `kafka2`, `kafka3` (kafka group) - Kafka brokers

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

## Common Failure Patterns

| Error Pattern | Likely Cause | Fix Location |
|--------------|--------------|--------------|
| `'variable_name' is undefined` | Missing variable | `defaults/main.yml` or `vars/*.yml` |
| `conditional check ... failed` | Undefined in `when:` | Define before conditional |
| `No file was found` | Missing template/file | `templates/` or `files/` |
| `handler not found` | Handler name mismatch | Match `notify:` with handler `name:` |
