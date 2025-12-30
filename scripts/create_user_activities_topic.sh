#!/bin/bash

# Configuration for user-activities topic
BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
TOPIC="${KAFKA_ACTIVITIES_TOPIC:-user-activities}"
PARTITIONS="${KAFKA_ACTIVITIES_PARTITIONS:-6}"
REPLICATION_FACTOR="${KAFKA_REPLICATION_FACTOR:-1}"
RETENTION_MS="${KAFKA_RETENTION_MS:-604800000}"  # 7 days in milliseconds

echo "=========================================="
echo "Creating User Activities Topic"
echo "=========================================="
echo "Topic: $TOPIC"
echo "Bootstrap servers: $BOOTSTRAP_SERVERS"
echo "Partitions: $PARTITIONS"
echo "Replication factor: $REPLICATION_FACTOR"
echo "Retention: 7 days ($RETENTION_MS ms)"
echo ""

# Check if topic already exists
echo "Checking if topic exists..."
EXISTS=$(docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
  --list --topic "$TOPIC" 2>/dev/null | grep -c "^${TOPIC}$" || echo "0")

if [ "$EXISTS" = "1" ]; then
    echo "Topic '$TOPIC' already exists."
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting existing topic..."
        docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
          --delete --topic "$TOPIC" 2>/dev/null || echo "Failed to delete (may not exist)"
        sleep 2
    else
        echo "Keeping existing topic. Exiting."
        exit 0
    fi
fi

# Create topic
echo "Creating topic..."
docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
  --create \
  --topic "$TOPIC" \
  --partitions "$PARTITIONS" \
  --replication-factor "$REPLICATION_FACTOR" \
  --config retention.ms="$RETENTION_MS" \
  --config retention.bytes=-1 \
  --if-not-exists

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Topic created successfully!"
    echo ""
    echo "Topic details:"
    docker exec kafka kafka-topics --bootstrap-server "$BOOTSTRAP_SERVERS" \
      --describe --topic "$TOPIC"
    
    echo ""
    echo "Topic configuration:"
    docker exec kafka kafka-configs --bootstrap-server "$BOOTSTRAP_SERVERS" \
      --entity-type topics \
      --entity-name "$TOPIC" \
      --describe 2>/dev/null || echo "Could not retrieve detailed config"
else
    echo "❌ Failed to create topic"
    exit 1
fi

echo ""
echo "=========================================="
echo "Topic ready for user activity events!"
echo "=========================================="

