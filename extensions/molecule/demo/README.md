# Molecule Demo Scenario

This scenario populates your Kafka cluster with demo data for presentations and screen recordings.

## Prerequisites

First, run the default scenario to set up the infrastructure:

```bash
molecule converge
```

## Usage

### Populate Demo Data

```bash
molecule converge -s demo
```

This will:
- Create 5 topics with various partition/replica configurations
- Produce ~575 sample messages with realistic JSON payloads
- Start 3 consumer groups to show active consumption

### Verify Demo Data

```bash
molecule verify -s demo
```

This validates:
- All topics exist with correct partition counts
- Messages are present in all topics
- Consumer groups are active and consuming
- Kafka UI can display the data

### Full Workflow

```bash
# 1. Set up infrastructure
molecule converge

# 2. Populate demo data
molecule converge -s demo

# 3. Verify everything
molecule verify -s demo

# 4. View in Kafka UI
open http://localhost:8080/ui/clusters/kafka-cluster
```

## What Gets Created

### Topics

| Topic | Partitions | Replicas | Messages | Configuration |
|-------|------------|----------|----------|---------------|
| user-events | 6 | 3 | ~100 | 7-day retention |
| order-processing | 4 | 3 | ~50 | 1-day retention |
| analytics-data | 8 | 3 | ~200 | Default |
| notifications | 3 | 2 | ~75 | Default |
| system-logs | 12 | 3 | ~150 | Gzip compression |

**Total:** 33 partitions, ~575 messages

### Consumer Groups

1. **user-events-analytics** - consuming from `user-events`
2. **order-fulfillment** - consuming from `order-processing`
3. **analytics-processors** - consuming from `analytics-data`

## Expected Kafka UI Metrics

After running this scenario, you should see:

```
Partitions
  Online: 33 of 33
  URP: 0

In Sync Replicas
  89 of 89

Out Of Sync Replicas
  0

Topics: 5
Consumer Groups: 3
```

## Cleanup

To remove demo data and start fresh:

```bash
# Just destroy and recreate
molecule destroy
molecule converge
```

## Notes

- This scenario inherits infrastructure from the `default` scenario
- Only works with plaintext (non-TLS) clusters currently
- Consumer groups run in the background on kafka1 and kafka2 nodes
- All tasks are idempotent - safe to run multiple times
