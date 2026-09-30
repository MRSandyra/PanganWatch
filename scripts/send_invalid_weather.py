"""F6: send 3 deliberately invalid messages to weather.current.raw.

Used to verify the consumer's DLQ path: each of these must fail
WeatherCurrentV1 validation and end up on weather.current.dlq (Lampiran C).

Usage:
    uv run python scripts/send_invalid_weather.py
"""

from __future__ import annotations

import json
import os
import sys
import time

from confluent_kafka import Producer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "weather.current.raw")

# 1) Missing required field (no kode_provinsi_bps)
MSG_MISSING_FIELD = {
    "event_id": "invalid-missing-field",
    "schema_version": "1.0",
    "observed_at": "2026-09-23T00:00:00+00:00",
    "temperature_c": 28.0,
    "source": "open-meteo",
    "fetched_at": "2026-09-23T00:00:00+00:00",
    "producer_id": "send_invalid_weather.py",
}

# 2) Wrong type (temperature_c as a string, not a number)
MSG_WRONG_TYPE = {
    "event_id": "invalid-wrong-type",
    "schema_version": "1.0",
    "kode_provinsi_bps": "31",
    "observed_at": "2026-09-23T00:00:00+00:00",
    "temperature_c": "sangat panas",
    "source": "open-meteo",
    "fetched_at": "2026-09-23T00:00:00+00:00",
    "producer_id": "send_invalid_weather.py",
}

# 3) Impossible value (temperature_c far outside -10..50 range)
MSG_IMPOSSIBLE_VALUE = {
    "event_id": "invalid-impossible-value",
    "schema_version": "1.0",
    "kode_provinsi_bps": "31",
    "observed_at": "2026-09-23T00:00:00+00:00",
    "temperature_c": 999.0,
    "source": "open-meteo",
    "fetched_at": "2026-09-23T00:00:00+00:00",
    "producer_id": "send_invalid_weather.py",
}

INVALID_MESSAGES = [
    ("missing required field (kode_provinsi_bps)", MSG_MISSING_FIELD),
    ("wrong type (temperature_c as string)", MSG_WRONG_TYPE),
    ("impossible value (temperature_c=999)", MSG_IMPOSSIBLE_VALUE),
]


def delivery_report(err, msg):
    if err is not None:
        print(f"  FAILED to deliver: {err}")
    else:
        print(f"  delivered to {msg.topic()} [{msg.partition()}] offset {msg.offset()}")


def main() -> int:
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP, "acks": "all"})
    for description, message in INVALID_MESSAGES:
        print(f"Sending invalid message: {description}")
        producer.produce(
            topic=KAFKA_TOPIC_RAW,
            key=message.get("kode_provinsi_bps", "unknown"),
            value=json.dumps(message),
            on_delivery=delivery_report,
        )
        producer.flush(timeout=10)
        time.sleep(0.2)
    print(f"Sent {len(INVALID_MESSAGES)} invalid messages to {KAFKA_TOPIC_RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
