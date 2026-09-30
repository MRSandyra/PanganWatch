"""Stream producer for current weather data into Kafka.

Fetches current weather (Open-Meteo) for 38 province capitals, builds a Kafka
message matching the `WeatherCurrentV1` contract, and sends it to the
`weather.current.raw` topic. The producer enables acks=all and idempotence
(confluent-kafka).

Usage:
    uv run python -m panganwatch.stream.producer --once
    uv run python -m panganwatch.stream.producer --once --loop 3

Args:
    --once            One polling cycle: fetch once and exit.
    --loop N          N cycles (default 1); wait `interval` between polls.
    --interval SECONDS polling interval in seconds (default 900).
    --bootstrap BROKER Kafka bootstrap address.
    --topic TOPIC     Kafka topic to send to (default weather.current.raw).
    --help            show this help and exit.
"""

import argparse
import asyncio
import json
import os
import time
from datetime import UTC, datetime

from confluent_kafka import Producer
from httpx import AsyncClient

from panganwatch.db import get_postgres_connection
from panganwatch.stream.models import WeatherCurrentV1

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "weather.current.raw")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "900"))
PRODUCER_ID = os.getenv("PRODUCER_ID", "weather-producer-1")


def load_province_codes_from_db() -> list[dict]:
    """Load the 38 BPS province codes and their coordinates from ref.ref_provinsi in Postgres."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT kode_bps, nama_provinsi, lat, lon
            FROM ref.ref_provinsi
            ORDER BY kode_bps
        """)
        rows = cur.fetchall()
        return [{"kode_bps": row[0], "nama": row[1], "lat": row[2], "lon": row[3]} for row in rows]
    finally:
        conn.close()


async def fetch_weather_for_province(client: AsyncClient, lat: float, lon: float) -> dict:
    """Fetch current weather for a province from the Open-Meteo API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "cloud_cover",
            "visibility",
            "pressure_msl",
            "uv_index",
        ],
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Jakarta",
        "forecast_hours": 0,
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("current", {})
        # The API returns visibility in metres; the contract uses km
        vis_m = data.get("visibility")
        data["visibility_km"] = None if vis_m is None else vis_m / 1000.0
        return data
    except Exception as e:
        print(f"    ERROR fetch {lat},{lon}: {e}")
        return {}


def create_kafka_message(prov_code: str, weather_data: dict, run_id: str) -> dict:
    """Build a Kafka message matching WeatherCurrentV1.

    Assumes `weather_data` is a dict shaped like the Open-Meteo API response
    (fields: temperature_2m, relative_humidity_2m, precipitation, ...) with
    `visibility_km` already converted from metres by
    `fetch_weather_for_province`.
    """
    event_id = f"{run_id}-{prov_code}"
    observed_at = datetime.now(UTC).isoformat()
    fetched_at = observed_at

    # The Open-Meteo API returns a `precipitation` field (not precipitation_mm)
    payload = WeatherCurrentV1(
        event_id=event_id,
        schema_version="1.0",
        kode_provinsi_bps=prov_code,
        observed_at=observed_at,
        temperature_c=weather_data.get("temperature_2m"),
        precipitation_mm=weather_data.get("precipitation"),
        humidity_pct=weather_data.get("relative_humidity_2m"),
        wind_speed_kph=weather_data.get("wind_speed_10m"),
        wind_direction_deg=weather_data.get("wind_direction_10m"),
        cloud_cover_pct=weather_data.get("cloud_cover"),
        visibility_km=weather_data.get("visibility_km"),
        pressure_hpa=weather_data.get("pressure_msl"),
        uv_index=int(weather_data.get("uv_index"))
        if weather_data.get("uv_index") is not None
        else None,
        sunrise_at=None,
        sunset_at=None,
        moon_phase=None,
        rain_mm=weather_data.get("rain"),
        weather_code=weather_data.get("weather_code"),
        source="open-meteo",
        fetched_at=fetched_at,
        producer_id=PRODUCER_ID,
    )
    return payload.model_dump(exclude_none=True)


def build_weather_message(
    province_code: str,
    province_name: str,
    lat: float,
    lon: float,
    temperature_c: float | None,
    precipitation_mm: float | None,
    humidity_pct: int | None,
    wind_speed_kph: float | None,
    wind_direction_deg: int | None,
    cloud_cover_pct: int | None,
    source_station: str,
) -> WeatherCurrentV1:
    """Build a WeatherCurrentV1 message for testing (offline).

    `source_station` maps to the contract's `producer_id` (Appendix C) — kept
    as a parameter name for backward compatibility with existing callers/tests.
    """
    from datetime import UTC, datetime

    event_id = f"test-{province_code}-{int(datetime.now(UTC).timestamp())}"
    now = datetime.now(UTC).isoformat()
    return WeatherCurrentV1(
        event_id=event_id,
        schema_version="1.0",
        kode_provinsi_bps=province_code,
        observed_at=now,
        temperature_c=temperature_c,
        precipitation_mm=precipitation_mm,
        humidity_pct=humidity_pct,
        wind_speed_kph=wind_speed_kph,
        wind_direction_deg=wind_direction_deg,
        cloud_cover_pct=cloud_cover_pct,
        visibility_km=None,
        pressure_hpa=None,
        uv_index=None,
        sunrise_at=None,
        sunset_at=None,
        moon_phase=None,
        source="open-meteo",
        fetched_at=now,
        producer_id=source_station,
    )


def delivery_report(err, msg):
    if err is not None:
        print(f"Failed to send message: {err}")
    else:
        print(f"Delivered to {msg.topic()} [{msg.partition()}] offset {msg.offset()}")


async def run_once(client: AsyncClient, producer: Producer, run_id: str):
    """Fetch data for every province and send it to Kafka."""
    print(f"Starting polling cycle (run_id={run_id}) ...")
    provinces = load_province_codes_from_db()
    success_count = 0
    for i, prov in enumerate(provinces, 1):
        print(f"  [{i}/{len(provinces)}] processing {prov['kode_bps']} ({prov['nama']})...")
        weather = await fetch_weather_for_province(client, prov["lat"], prov["lon"])
        if not weather:
            print("    ⚠️ no data, skipping")
            continue
        msg = create_kafka_message(prov["kode_bps"], weather, run_id)
        producer.produce(
            topic=KAFKA_TOPIC,
            key=prov["kode_bps"],
            value=json.dumps(msg),
            on_delivery=delivery_report,
        )
        producer.flush()
        success_count += 1
        await asyncio.sleep(0.2)
    print(f"Cycle complete: {success_count}/{len(provinces)} messages sent.")


async def main():
    global KAFKA_BOOTSTRAP, KAFKA_TOPIC
    parser = argparse.ArgumentParser(description="Kafka weather producer")
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle only")
    parser.add_argument("--loop", type=int, default=1, help="Number of cycles (default 1)")
    parser.add_argument(
        "--interval",
        type=int,
        default=POLL_INTERVAL_SECONDS,
        help="Interval between cycles (seconds)",
    )
    parser.add_argument("--bootstrap", default=KAFKA_BOOTSTRAP, help="Kafka bootstrap address")
    parser.add_argument("--topic", default=KAFKA_TOPIC, help="Kafka topic")
    args = parser.parse_args()

    KAFKA_BOOTSTRAP = args.bootstrap
    KAFKA_TOPIC = args.topic

    producer_config = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "acks": "all",
        "enable.idempotence": True,
        "max.in.flight.requests.per.connection": 1,
        "retries": 5,
    }
    producer = Producer(producer_config)

    async with AsyncClient(timeout=30.0) as client:
        for cycle in range(args.loop):
            run_id = f"{int(time.time())}-{cycle}"
            await run_once(client, producer, run_id)
            if not args.once and cycle < args.loop - 1:
                print(f"Waiting {args.interval} seconds before the next cycle...")
                await asyncio.sleep(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
