---
agent: agent
description: Run complete Molecule test workflow with autonomous fix-and-retry loop until all tests pass
tools:
  ['execute', 'read', 'edit', 'search', 'web', 'agent', 'copilot-container-tools/*', 'todo']
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
│  7. SUCCESS → Report completion, keep infra running     │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: Converge

```bash
molecule converge 2>&1 | grep -E "(FAILED|fatal:|ERROR|PLAY RECAP|Scenario|changed=|ok=)" -A 15
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

## Autonomous Fix Loop

When ANY phase fails:

1. **Analyze the error** - Identify the failing task, role, and root cause
2. **Read relevant files** - Check the task file, variable definitions, templates
3. **Implement the fix** - Edit the appropriate file(s)
4. **Re-run from Phase 1** - Always restart from converge after fixes
5. **Track attempts** - Keep count of fix attempts per issue

### Diagnostic Commands (use as needed)

```bash
# Check service status
docker exec -it zk1 systemctl status zookeeper
docker exec -it kafka1 systemctl status kafka

# View service logs
docker exec -it zk1 journalctl -u zookeeper -n 100 --no-pager
docker exec -it kafka1 journalctl -u kafka -n 100 --no-pager

# Check ZooKeeper
docker exec -it zk1 /opt/zookeeper/bin/zkServer.sh status

# Check Kafka
docker exec -it kafka1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# View config files
docker exec -it kafka1 cat /opt/kafka/config/server.properties
docker exec -it zk1 cat /opt/zookeeper/conf/zoo.cfg
```

### Common Fixes

| Error Pattern | Likely Fix |
|---------------|------------|
| `'variable' is undefined` | Add to `roles/<role>/defaults/main.yml` or `vars/*.yml` |
| `No file was found` | Create missing template in `roles/<role>/templates/` |
| `handler not found` | Match `notify:` name with handler `name:` in `handlers/main.yml` |
| `conditional check failed` | Ensure variable is defined before the `when:` clause |
| Service won't start | Check logs with `journalctl`, fix config templates |
| `changed != 0` in idempotence | Make task conditional or use `creates:`/`removes:` |

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
- Infrastructure remains running for manual verification

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
