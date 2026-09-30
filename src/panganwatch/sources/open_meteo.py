"""F3c: historical daily weather for the 38 provincial capitals (Open-Meteo Archive API).

Docs: https://open-meteo.com/en/docs/historical-weather-api
Multi-location requests are supported by passing comma-separated
`latitude`/`longitude` lists; the response is a JSON array in the same order
as the input coordinates (verified against the live API in this session).

CLI: `uv run python -m panganwatch.sources.open_meteo --backfill`
"""

from __future__ import annotations

import argparse
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from panganwatch.bronze import store_raw
from panganwatch.config import get_settings
from panganwatch.db import get_postgres_connection
from panganwatch.governance.pipeline_runs import finish_run, start_run
from panganwatch.silver.cuaca_harian import upsert_cuaca_harian

SOURCE_NAME = "Open-Meteo Archive"
MONGO_COLLECTION = "open_meteo_daily"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "precipitation_sum,temperature_2m_max,temperature_2m_min"
# Open-Meteo advises chunking multi-location requests to keep URLs and
# per-call payloads reasonable; 38 provinces fits comfortably in one call
# (verified against the live API), but chunk defensively for large date ranges.
MAX_LOCATIONS_PER_REQUEST = 38


def load_provinces() -> list[dict[str, Any]]:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT kode_bps, nama_provinsi, lat, lon FROM ref.ref_provinsi ORDER BY kode_bps"
            )
            return [
                {"kode_bps": row[0], "nama_provinsi": row[1], "lat": row[2], "lon": row[3]}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def fetch_archive(
    provinces: list[dict[str, Any]], start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Call the Archive API for a batch of provinces; returns the raw JSON list
    (one object per province, same order as `provinces`)."""
    params = {
        "latitude": ",".join(str(p["lat"]) for p in provinces),
        "longitude": ",".join(str(p["lon"]) for p in provinces),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": DAILY_VARS,
        "timezone": "Asia/Jakarta",
    }
    resp = httpx.get(ARCHIVE_URL, params=params, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def to_daily_records(
    province: dict[str, Any], daily_response: dict[str, Any], source_label: str
) -> list[dict[str, Any]]:
    """Pure function: turn one province's Archive API `daily` block into
    silver.cuaca_harian record dicts."""
    daily = daily_response.get("daily", {})
    times = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])

    records = []
    for i, tanggal in enumerate(times):
        records.append(
            {
                "tanggal": tanggal,
                "kode_provinsi_bps": province["kode_bps"],
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "tmax_c": tmax[i] if i < len(tmax) else None,
                "tmin_c": tmin[i] if i < len(tmin) else None,
                "source": source_label,
            }
        )
    return records


def run_ingestion(start_date: date, end_date: date, run_id: str) -> tuple[int, int, int]:
    provinces = load_provinces()
    rows_fetched = 0
    rows_loaded = 0
    rows_quarantined = 0

    conn = get_postgres_connection()
    try:
        for i in range(0, len(provinces), MAX_LOCATIONS_PER_REQUEST):
            batch = provinces[i : i + MAX_LOCATIONS_PER_REQUEST]
            responses = fetch_archive(batch, start_date, end_date)
            # `generationtime_ms` is the API's own processing-time metric, not
            # weather data; it varies on every call and would otherwise make
            # the bronze payload hash (and idempotency) non-deterministic.
            for resp in responses:
                resp.pop("generationtime_ms", None)

            store_raw(
                source="open_meteo_archive",
                endpoint=ARCHIVE_URL,
                params={
                    "provinces": [p["kode_bps"] for p in batch],
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "daily": DAILY_VARS,
                },
                payload=responses,
                http_status=200,
                run_id=run_id,
                collection=MONGO_COLLECTION,
            )

            for province, resp in zip(batch, responses):
                records = to_daily_records(province, resp, SOURCE_NAME)
                for record in records:
                    rows_fetched += 1
                    if record["precipitation_mm"] is None:
                        rows_quarantined += 1
                        continue
                    record["run_id"] = run_id
                    upsert_cuaca_harian(record, conn=conn)
                    rows_loaded += 1

            if i + MAX_LOCATIONS_PER_REQUEST < len(provinces):
                time.sleep(1.0)  # politeness delay between batched requests
    finally:
        conn.close()

    return rows_fetched, rows_loaded, rows_quarantined


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m panganwatch.sources.open_meteo",
        description="Ingest historical daily weather for 38 provincial capitals (Open-Meteo Archive API) into bronze/silver (F3c).",
    )
    p.add_argument("--backfill", action="store_true", help="Run the backfill ingestion")
    p.add_argument("--start-date", type=str, default=None, help="Window start (YYYY-MM-DD)")
    p.add_argument(
        "--end-date", type=str, default=None, help="Window end (YYYY-MM-DD), default: today"
    )
    p.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help="Days before --end-date to backfill (default: config/settings.yaml ingestion.backfill_days)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.backfill:
        build_arg_parser().print_help()
        return 0

    settings = get_settings()
    backfill_days = args.backfill_days or settings.ingestion["backfill_days"]
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else date.today()
    )
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date
        else end_date - timedelta(days=backfill_days)
    )

    run_id = str(uuid.uuid4())
    start_run(run_id, SOURCE_NAME)
    print(f"[Open-Meteo] run_id={run_id} window={start_date}..{end_date}")

    try:
        rows_fetched, rows_loaded, rows_quarantined = run_ingestion(start_date, end_date, run_id)
    except Exception as exc:  # noqa: BLE001
        finish_run(run_id, SOURCE_NAME, "failed", error_message=str(exc))
        print(f"[Open-Meteo] FAILED: {exc}")
        raise

    status = "success" if rows_quarantined == 0 else "partial"
    finish_run(run_id, SOURCE_NAME, status, rows_fetched, rows_loaded, rows_quarantined)
    print(
        f"[Open-Meteo] done: fetched={rows_fetched} loaded={rows_loaded} "
        f"quarantined={rows_quarantined} status={status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
