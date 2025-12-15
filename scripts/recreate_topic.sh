#!/bin/bash

# Default values
BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
TOPIC="${KAFKA_TOPIC:-car_parts_published}"
PARTITIONS="${KAFKA_PARTITIONS:-3}"
REPLICATION_FACTOR="${KAFKA_REPLICATION_FACTOR:-1}"

echo "Recreating topic: $TOPIC"
echo "Bootstrap servers: $BOOTSTRAP_SERVERS"
echo "Partitions: $PARTITIONS"
echo "Replication factor: $REPLICATION_FACTOR"
echo ""

# Delete topic if it exists
echo "Deleting topic (if exists)..."
docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
  --delete --topic "$TOPIC" 2>/dev/null || echo "Topic does not exist, skipping delete"

# Wait a moment for deletion to complete
sleep 2

# Create topic
echo "Creating topic..."
docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
  --create --topic "$TOPIC" \
  --partitions "$PARTITIONS" \
  --replication-factor "$REPLICATION_FACTOR"

# Verify topic creation
echo ""
echo "Topic details:"
docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
  --describe --topic "$TOPIC"

