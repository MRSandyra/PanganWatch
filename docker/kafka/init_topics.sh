# Docker init script for PanganWatch Kafka topics
# Run once after Kafka is healthy

#!/usr/bin/env bash
set -e

echo "Checking Kafka topics..."

# Wait for Kafka to be ready
until docker compose exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
    echo "Waiting for Kafka..."
    sleep 2
done

# Create each topic if it doesn't exist yet
for topic in weather.current.raw weather.current.dlq weather.alert; do
    if ! docker compose exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -q "^${topic}$"; then
        echo "Creating topic ${topic}..."
        docker compose exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --create \
            --topic ${topic} \
            --partitions $( [ "$topic" = "weather.current.raw" ] && echo 3 || echo 1 ) \
            --replication-factor 1 \
            --config retention.ms=604800000 \
            --if-not-exists
    else
        echo "Topic ${topic} already exists"
    fi
done

echo "Kafka initialization complete"
