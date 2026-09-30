"""Stream consumer for the raw-weather Kafka topic; sends to silver+DLQ.

Every message is validated against WeatherCurrentV1. If valid, it is upserted
into `silver.cuaca_terkini` and the raw payload is stored in bronze
`open_meteo_current`. If invalid, it is sent to the Kafka DLQ topic
(`weather.current.dlq`) with `error_reason`/`original_topic`/`original_offset`/
`failed_at` headers (Appendix C) -- the offset is still committed afterward (a
bad message is "handled", not blocked forever). If rainfall >= the threshold
(settings.weather.alert.precipitation_mm_threshold), a `WeatherAlertV1` is sent
to the Kafka `weather.alert` topic and written to `governance.weather_alerts`.
"""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from confluent_kafka import Consumer, KafkaError, Producer
from pydantic import ValidationError

from panganwatch.bronze import store_raw
from panganwatch.config import get_settings
from panganwatch.db import get_postgres_connection
from panganwatch.stream.models import WeatherAlertV1, WeatherCurrentV1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "weather.current.raw")
KAFKA_TOPIC_DLQ = os.getenv("KAFKA_TOPIC_DLQ", "weather.current.dlq")
KAFKA_TOPIC_ALERT = os.getenv("KAFKA_TOPIC_ALERT", "weather.alert")
CONSUMER_GROUP_ID = "panganwatch-weather-sink"
MONGO_COLLECTION_CURRENT = "open_meteo_current"

settings = get_settings()
# settings.weather is a dict, not an object
weather_dict = settings.weather
ALERT_THRESHOLD_MM = weather_dict.get("alert", {}).get("precipitation_mm_threshold", 50.0)


async def get_postgres_connection_async():
    """Get PostgreSQL connection in async context.

    Since PanganWatch uses synchronous psycopg, we'll run the connection
    in a thread pool to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    conn = await loop.run_in_executor(None, lambda: get_postgres_connection())
    return conn


async def _reconnect_postgres(conn):
    """Best-effort reconnect after a dropped connection (e.g. Postgres container
    restart mid-run leaves the old socket dead — every message would otherwise
    fail forever with "the connection is closed/lost")."""
    try:
        conn.close()
    except Exception:
        pass
    return await get_postgres_connection_async()


async def upsert_to_silver(message: dict, conn):
    """Upsert weather data to silver.cuaca_terkini.

    The table schema:
    CREATE TABLE IF NOT EXISTS silver.cuaca_terkini (
        kode_provinsi_bps TEXT NOT NULL,
        observed_at TIMESTAMP NOT NULL,
        temperature_c REAL,
        precipitation_mm REAL,
        humidity_pct REAL,
        wind_speed_kph REAL,
        wind_direction_deg REAL,
        cloud_cover_pct REAL,
        visibility_km REAL,
        pressure_hpa REAL,
        uv_index INTEGER,
        sunrise_at TIMESTAMP,
        sunset_at TIMESTAMP,
        moon_phase REAL,
        PRIMARY KEY (kode_provinsi_bps, observed_at)
    );
    """
    try:
        cur = conn.cursor()

        observed_at = datetime.fromisoformat(message["observed_at"])
        sunrise_at = None
        sunset_at = None
        if "sunrise_at" in message and message["sunrise_at"]:
            sunrise_at = datetime.fromisoformat(message["sunrise_at"])
        if "sunset_at" in message and message["sunset_at"]:
            sunset_at = datetime.fromisoformat(message["sunset_at"])

        query = """
        INSERT INTO silver.cuaca_terkini
        (kode_provinsi_bps, observed_at, temperature_c, precipitation_mm,
         humidity_pct, wind_speed_kph, wind_direction_deg, cloud_cover_pct,
         visibility_km, pressure_hpa, uv_index, sunrise_at, sunset_at, moon_phase)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (kode_provinsi_bps, observed_at) DO UPDATE SET
            temperature_c = EXCLUDED.temperature_c,
            precipitation_mm = EXCLUDED.precipitation_mm,
            humidity_pct = EXCLUDED.humidity_pct,
            wind_speed_kph = EXCLUDED.wind_speed_kph,
            wind_direction_deg = EXCLUDED.wind_direction_deg,
            cloud_cover_pct = EXCLUDED.cloud_cover_pct,
            visibility_km = EXCLUDED.visibility_km,
            pressure_hpa = EXCLUDED.pressure_hpa,
            uv_index = EXCLUDED.uv_index,
            sunrise_at = EXCLUDED.sunrise_at,
            sunset_at = EXCLUDED.sunset_at,
            moon_phase = EXCLUDED.moon_phase
        """

        cur.execute(
            query,
            (
                message["kode_provinsi_bps"],
                observed_at,
                message.get("temperature_c"),
                message.get("precipitation_mm"),
                message.get("humidity_pct"),
                message.get("wind_speed_kph"),
                message.get("wind_direction_deg"),
                message.get("cloud_cover_pct"),
                message.get("visibility_km"),
                message.get("pressure_hpa"),
                message.get("uv_index"),
                sunrise_at,
                sunset_at,
                message.get("moon_phase"),
            ),
        )

        conn.commit()
        logger.debug(
            f"Upserted weather data for {message['kode_provinsi_bps']} at {message['observed_at']}"
        )
        return True

    except Exception as e:
        logger.error(f"Error upserting to silver: {e}")
        conn.rollback()
        raise


def _kafka_delivery_log(err, msg):
    if err is not None:
        logger.error(f"Failed to send to {msg.topic()}: {err}")


async def write_to_dlq(
    raw_bytes: bytes,
    message: dict,
    error_reason: str,
    original_partition: int,
    original_offset: int,
    conn,
    producer: Producer,
):
    """Send an invalid message to the Kafka `weather.current.dlq` topic (Appendix C:
    the original payload unchanged, with error_reason/original_topic/
    original_offset/failed_at headers), and log it to governance.dlq_logs for audit."""
    try:
        failed_at = datetime.now(UTC).isoformat()
        headers = [
            ("error_reason", error_reason.encode("utf-8")),
            ("original_topic", KAFKA_TOPIC_RAW.encode("utf-8")),
            ("original_offset", str(original_offset).encode("utf-8")),
            ("failed_at", failed_at.encode("utf-8")),
        ]
        producer.produce(
            topic=KAFKA_TOPIC_DLQ,
            value=raw_bytes,
            headers=headers,
            on_delivery=_kafka_delivery_log,
        )
        producer.flush(timeout=10)

        cur = conn.cursor()
        query = """
        INSERT INTO governance.dlq_logs
        (event_id, original_topic, original_partition, original_offset,
         error_reason, raw_message, received_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        event_id = message.get("event_id", str(uuid4()))
        cur.execute(
            query,
            (
                event_id,
                KAFKA_TOPIC_RAW,
                original_partition,
                original_offset,
                error_reason,
                json.dumps(message),
                datetime.now(UTC),
            ),
        )
        conn.commit()
        logger.debug(f"Sent invalid message to DLQ topic + governance.dlq_logs: {error_reason}")

    except Exception as e:
        logger.error(f"Error writing to DLQ: {e}")
        conn.rollback()
        raise


async def send_alert(alert_data: dict, conn, producer: Producer):
    """Send a WeatherAlertV1 to the Kafka `weather.alert` topic and store it in governance.weather_alerts."""
    try:
        alert_msg = WeatherAlertV1(
            event_id=alert_data["event_id"],
            schema_version="1.0",
            kode_provinsi_bps=alert_data["kode_provinsi_bps"],
            alert_type=alert_data["alert_type"],
            alert_level=alert_data["alert_level"],
            threshold_field=alert_data["threshold_field"],
            threshold_value=alert_data["threshold_value"],
            current_value=alert_data["current_value"],
            observed_at=alert_data["observed_at"],
            valid_until=alert_data.get("valid_until"),
            recommendation=alert_data.get("recommendation"),
        )
        producer.produce(
            topic=KAFKA_TOPIC_ALERT,
            key=alert_data["kode_provinsi_bps"],
            value=alert_msg.model_dump_json(),
            on_delivery=_kafka_delivery_log,
        )
        producer.flush(timeout=10)

        cur = conn.cursor()

        query = """
        INSERT INTO governance.weather_alerts
        (event_id, kode_provinsi_bps, alert_type, alert_level, threshold_field,
         threshold_value, current_value, observed_at, valid_until, recommendation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(
            query,
            (
                alert_data["event_id"],
                alert_data["kode_provinsi_bps"],
                alert_data["alert_type"],
                alert_data["alert_level"],
                alert_data["threshold_field"],
                alert_data["threshold_value"],
                alert_data["current_value"],
                datetime.fromisoformat(alert_data["observed_at"]),
                alert_data.get("valid_until"),
                alert_data.get("recommendation"),
            ),
        )

        conn.commit()
        logger.debug(f"Stored weather alert for {alert_data['kode_provinsi_bps']}")

        logger.info(f"Weather alert generated: {alert_data}")

        return True

    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        conn.rollback()
        raise


async def process_message(msg, postgres_conn, producer: Producer, run_id: str):
    """Process a single Kafka message.

    Returns (postgres_conn, handled, error_reason). `postgres_conn` is returned
    because a dropped connection is transparently reconnected inside this
    function — the caller must keep using the returned connection object.
    `handled=True` means the offset should be committed — true both for a
    valid message written to silver AND for an invalid message successfully
    routed to the DLQ (at-least-once with an idempotent sink; a message we
    can't even attempt to handle due to a transient error returns
    handled=False so it gets redelivered).
    """
    raw_bytes = msg.value()
    try:
        raw_value = raw_bytes.decode("utf-8")
        message_data = json.loads(raw_value)

        validated_message = WeatherCurrentV1(**message_data)
        validated_dict = validated_message.model_dump(exclude_none=True)

        logger.info(
            f"Validated message for {validated_dict['kode_provinsi_bps']} at {validated_dict['observed_at']}"
        )

        await upsert_to_silver(validated_dict, postgres_conn)

        store_raw(
            source="open_meteo_current",
            endpoint="kafka:weather.current.raw",
            params={"kode_provinsi_bps": validated_dict["kode_provinsi_bps"]},
            payload=validated_dict,
            http_status=200,
            run_id=run_id,
            collection=MONGO_COLLECTION_CURRENT,
        )

        precipitation = validated_dict.get("precipitation_mm")
        if precipitation is not None and precipitation >= ALERT_THRESHOLD_MM:
            alert_data = {
                "event_id": str(uuid4()),
                "schema_version": "1.0",
                "kode_provinsi_bps": validated_dict["kode_provinsi_bps"],
                "alert_type": "heavy_rain",
                "alert_level": "heavy",
                "threshold_field": "precipitation_mm",
                "threshold_value": ALERT_THRESHOLD_MM,
                "current_value": precipitation,
                "observed_at": validated_dict["observed_at"],
                "valid_until": None,
                "recommendation": f"Rainfall {precipitation}mm exceeds {ALERT_THRESHOLD_MM}mm threshold",
            }
            await send_alert(alert_data, postgres_conn, producer)

        return postgres_conn, True, None

    except ValidationError as e:
        error_reason = f"Validation error: {str(e)}"
        logger.warning(f"Message validation failed: {error_reason}")

        try:
            raw_message = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            raw_message = {"raw_bytes": repr(raw_bytes)}

        try:
            await write_to_dlq(
                raw_bytes,
                raw_message,
                error_reason,
                msg.partition(),
                msg.offset(),
                postgres_conn,
                producer,
            )
            return postgres_conn, True, error_reason
        except Exception as dlq_error:
            logger.error(f"Error writing to DLQ: {dlq_error}")
            postgres_conn = await _reconnect_postgres(postgres_conn)
            return postgres_conn, False, str(dlq_error)

    except Exception as e:
        error_reason = f"Processing error: {str(e)}"
        logger.error(f"Error processing message: {error_reason}")
        postgres_conn = await _reconnect_postgres(postgres_conn)
        return postgres_conn, False, error_reason


async def consume_loop():
    """Main consumer loop."""
    consumer_config = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": CONSUMER_GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "max.poll.interval.ms": 300000,
        "session.timeout.ms": 30000,
        "enable.partition.eof": False,
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe([KAFKA_TOPIC_RAW])

    producer_config = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "acks": "all",
        "enable.idempotence": True,
    }
    producer = Producer(producer_config)

    postgres_conn = await get_postgres_connection_async()
    run_id = f"consumer-{int(datetime.now(UTC).timestamp())}"

    try:
        logger.info(f"Starting consumer for topic {KAFKA_TOPIC_RAW}")
        logger.info(f"Alert threshold: {ALERT_THRESHOLD_MM} mm")

        while True:
            try:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue

                postgres_conn, handled, error = await process_message(
                    msg, postgres_conn, producer, run_id
                )

                if handled:
                    consumer.commit()
                    logger.debug(f"Committed offset {msg.offset()} for partition {msg.partition()}")

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Fatal error in consumer: {e}")
        raise

    finally:
        if "postgres_conn" in locals():
            postgres_conn.close()
        if "producer" in locals():
            producer.flush(timeout=10)
        consumer.close()
        logger.info("Consumer shutdown complete")


async def main():
    """Main entry point."""
    logger.info("Starting PanganWatch weather stream consumer")
    logger.info(f"Kafka bootstrap: {KAFKA_BOOTSTRAP}")
    logger.info(f"Topic: {KAFKA_TOPIC_RAW}")
    logger.info(f"DLQ topic: {KAFKA_TOPIC_DLQ}")
    logger.info(f"Alert topic: {KAFKA_TOPIC_ALERT}")

    try:
        conn = await get_postgres_connection_async()
        conn.close()
        logger.info("PostgreSQL connection OK")
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        logger.error("Consumer cannot start without PostgreSQL connection")
        return

    await consume_loop()


if __name__ == "__main__":
    asyncio.run(main())
