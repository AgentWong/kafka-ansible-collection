#!/usr/bin/env python3
"""
Kafka Traffic Generator
Produces messages to multiple topics and consumes with intentional lag
to create realistic monitoring data for Prometheus/Grafana dashboards.

Configuration via environment variables:
  KAFKA_BOOTSTRAP_SERVERS  — comma-separated list (default: kafka1:9092,kafka2:9092,kafka3:9092)
  PRODUCE_INTERVAL         — seconds between produce batches (default: 2)
  CONSUME_INTERVAL         — seconds between consume polls (default: 5)
"""

import json
import logging
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("traffic_generator")

# Configuration
BOOTSTRAP_SERVERS = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9092,kafka3:9092"
).split(",")
PRODUCE_INTERVAL = float(os.environ.get("PRODUCE_INTERVAL", "2"))
CONSUME_INTERVAL = float(os.environ.get("CONSUME_INTERVAL", "5"))

TOPICS = [
    "user-events",
    "order-processing",
    "analytics-data",
    "notifications",
    "system-logs",
]

CONSUMER_GROUPS = [
    "analytics-consumer",
    "audit-consumer",
    "reporting-consumer",
]

# Global shutdown event
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    logger.info("Shutdown signal received, stopping...")
    shutdown_event.set()


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def wait_for_kafka(retries=30, delay=5):
    """Wait until Kafka brokers are reachable."""
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                request_timeout_ms=5000,
                max_block_ms=5000,
            )
            producer.close()
            logger.info("Kafka brokers reachable: %s", BOOTSTRAP_SERVERS)
            return True
        except NoBrokersAvailable:
            logger.info(
                "Waiting for Kafka brokers (attempt %d/%d)...", attempt + 1, retries
            )
            time.sleep(delay)
    logger.error("Kafka brokers not reachable after %d attempts", retries)
    return False


def producer_thread():
    """Continuously produce messages to all topics."""
    logger.info("Producer thread starting")
    producer = None

    while not shutdown_event.is_set():
        try:
            if producer is None:
                producer = KafkaProducer(
                    bootstrap_servers=BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                )

            for topic in TOPICS:
                message = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "topic": topic,
                    "event_id": random.randint(100000, 999999),
                    "user_id": f"user_{random.randint(1, 1000)}",
                    "payload": {
                        "action": random.choice(
                            ["create", "update", "delete", "view", "process"]
                        ),
                        "value": round(random.uniform(0.01, 9999.99), 2),
                        "status": random.choice(["success", "pending", "failed"]),
                    },
                }
                producer.send(topic, value=message)

            producer.flush()
            logger.debug("Produced batch to %d topics", len(TOPICS))

        except KafkaError as e:
            logger.warning("Producer error: %s — reconnecting", e)
            if producer:
                producer.close()
                producer = None
            time.sleep(5)
            continue

        shutdown_event.wait(PRODUCE_INTERVAL)

    if producer:
        producer.close()
    logger.info("Producer thread stopped")


def consumer_thread(group_id, topics, lag_delay):
    """Consume messages from given topics with an intentional processing delay."""
    logger.info("Consumer thread starting: group=%s delay=%.1fs", group_id, lag_delay)
    consumer = None

    while not shutdown_event.is_set():
        try:
            if consumer is None:
                consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=BOOTSTRAP_SERVERS,
                    group_id=group_id,
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    consumer_timeout_ms=int(CONSUME_INTERVAL * 1000),
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                )

            records = consumer.poll(timeout_ms=int(CONSUME_INTERVAL * 1000))
            count = sum(len(msgs) for msgs in records.values())
            if count:
                logger.debug("group=%s consumed %d messages", group_id, count)
                # Intentional variable delay to create measurable consumer lag
                time.sleep(lag_delay)

        except KafkaError as e:
            logger.warning("Consumer error [%s]: %s — reconnecting", group_id, e)
            if consumer:
                consumer.close()
                consumer = None
            time.sleep(5)
            continue

        if shutdown_event.is_set():
            break

    if consumer:
        consumer.close()
    logger.info("Consumer thread stopped: group=%s", group_id)


def main():
    logger.info(
        "Traffic generator starting — brokers: %s", ", ".join(BOOTSTRAP_SERVERS)
    )

    if not wait_for_kafka():
        sys.exit(1)

    threads = []

    # Producer thread
    p = threading.Thread(target=producer_thread, name="producer", daemon=True)
    threads.append(p)
    p.start()

    # Consumer threads — each with a different lag profile
    consumer_configs = [
        ("analytics-consumer", ["user-events", "analytics-data"], 1.0),
        ("audit-consumer", ["user-events", "order-processing", "system-logs"], 8.0),
        ("reporting-consumer", ["order-processing", "analytics-data", "notifications"], 15.0),
    ]

    for group_id, topics, lag_delay in consumer_configs:
        t = threading.Thread(
            target=consumer_thread,
            args=(group_id, topics, lag_delay),
            name=f"consumer-{group_id}",
            daemon=True,
        )
        threads.append(t)
        t.start()

    logger.info("All threads running — producer + %d consumers", len(consumer_configs))

    # Wait for shutdown
    shutdown_event.wait()

    logger.info("Waiting for threads to finish...")
    for t in threads:
        t.join(timeout=15)

    logger.info("Traffic generator stopped")


if __name__ == "__main__":
    main()
