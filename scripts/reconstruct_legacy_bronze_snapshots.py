"""Reconstruct immutable replay snapshots from exported legacy Mongo Bronze documents."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from databricks.src.manifest import build_manifest, sha256_file, write_manifest  # noqa: E402

WFP_FILE_NAME = "legacy_hdx_wfp_replay.csv"
WEATHER_FILE_NAME = "legacy_open_meteo_replay.jsonl"
WFP_COLUMNS = [
    "date",
    "admin1",
    "admin2",
    "market",
    "market_id",
    "latitude",
    "longitude",
    "category",
    "commodity",
    "commodity_id",
    "unit",
    "priceflag",
    "pricetype",
    "currency",
    "price",
    "usdprice",
]


def read_documents(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    documents = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not documents:
        raise ValueError(f"No documents found in {path}")
    for document in documents:
        if not {"_meta", "payload"}.issubset(document):
            raise ValueError(f"Invalid Bronze envelope in {path}")
    return documents


def timestamp(document: dict[str, Any]) -> datetime:
    value = document["_meta"]["fetched_at"]
    if isinstance(value, dict):
        value = value.get("$date")
    if not isinstance(value, str):
        raise ValueError(f"Invalid _meta.fetched_at: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def period(rows: list[dict[str, Any]]) -> tuple[str, str]:
    values = sorted(date.fromisoformat(str(row["date"])) for row in rows)
    return values[0].isoformat(), values[-1].isoformat()


def replay_price_rows(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the legacy upsert ordering to source-native WFP rows."""
    latest: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for document in sorted(documents, key=timestamp):
        payload = document["payload"]
        if not isinstance(payload, list):
            raise ValueError("Expected WFP payload to be an array")
        for row in payload:
            if not isinstance(row, dict) or any(column not in row for column in WFP_COLUMNS):
                raise ValueError("WFP payload does not match the expected source-native CSV fields")
            key = tuple(
                str(row[column] or "") for column in ("date", "admin1", "market", "commodity")
            )
            latest[key] = {column: row[column] for column in WFP_COLUMNS}
    return [latest[key] for key in sorted(latest)]


def replay_weather_rows(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the legacy upsert ordering to Open-Meteo payload envelopes."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for document in sorted(documents, key=timestamp):
        provinces = document["_meta"]["params"].get("provinces")
        payload = document["payload"]
        if (
            not isinstance(provinces, list)
            or not isinstance(payload, list)
            or len(provinces) != len(payload)
        ):
            raise ValueError("Weather payload/province metadata cardinality mismatch")
        for province, response in zip(provinces, payload, strict=True):
            daily = response.get("daily", {}) if isinstance(response, dict) else {}
            times = daily.get("time", [])
            precipitation = daily.get("precipitation_sum", [])
            tmax = daily.get("temperature_2m_max", [])
            tmin = daily.get("temperature_2m_min", [])
            if not all(len(values) == len(times) for values in (precipitation, tmax, tmin)):
                raise ValueError("Weather daily arrays have inconsistent lengths")
            for index, value in enumerate(times):
                key = (str(province), str(value))
                latest[key] = {
                    "kode_provinsi_bps": str(province),
                    "date": str(value),
                    "precipitation_sum": precipitation[index],
                    "temperature_2m_max": tmax[index],
                    "temperature_2m_min": tmin[index],
                }

    per_province: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in latest.values():
        per_province[row["kode_provinsi_bps"]].append(row)
    output = []
    for province, rows in sorted(per_province.items()):
        rows.sort(key=lambda row: row["date"])
        output.append(
            {
                "requested_province": {"kode_provinsi_bps": province},
                "request": {"source": "legacy_mongodb_bronze_replay"},
                "response": {
                    "daily": {
                        "time": [row["date"] for row in rows],
                        "precipitation_sum": [row["precipitation_sum"] for row in rows],
                        "temperature_2m_max": [row["temperature_2m_max"] for row in rows],
                        "temperature_2m_min": [row["temperature_2m_min"] for row in rows],
                    }
                },
            }
        )
    return output


def write_provenance(
    path: Path,
    *,
    dataset: str,
    source_export: Path,
    documents: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            {
                "dataset": dataset,
                "legacy_mongodb_export": source_export.name,
                "legacy_mongodb_export_sha256": sha256_file(source_export),
                "legacy_bronze_document_count": len(documents),
                "legacy_run_ids": sorted({document["_meta"]["run_id"] for document in documents}),
                "replay_snapshot_id": manifest["snapshot_id"],
                "replay_snapshot_sha256": manifest["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wfp-export", required=True, type=Path)
    parser.add_argument("--weather-export", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()

    wfp_documents = read_documents(args.wfp_export)
    weather_documents = read_documents(args.weather_export)
    price_rows = replay_price_rows(wfp_documents)
    weather_rows = replay_weather_rows(weather_documents)
    args.destination.mkdir(parents=True, exist_ok=True)
    price_path = args.destination / WFP_FILE_NAME
    weather_path = args.destination / WEATHER_FILE_NAME
    paths = [
        price_path,
        weather_path,
        price_path.with_suffix(".csv.manifest.json"),
        weather_path.with_suffix(".jsonl.manifest.json"),
    ]
    if any(path.exists() for path in paths):
        raise FileExistsError(
            f"Refusing to overwrite existing replay artifact in {args.destination}"
        )

    with price_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WFP_COLUMNS)
        writer.writeheader()
        writer.writerows(price_rows)
    price_start, price_end = period(price_rows)
    price_manifest = build_manifest(
        price_path,
        source_name="legacy_hdx_wfp_replay",
        source_url="legacy-mongodb-export:bronze/hdx_wfp_prices",
        license_name="CC-BY-IGO",
        source_period_start=price_start,
        source_period_end=price_end,
    )
    write_manifest(price_manifest, price_path.with_suffix(".csv.manifest.json"))
    write_provenance(
        args.destination / "legacy_hdx_wfp_replay.provenance.json",
        dataset="harga_pangan",
        source_export=args.wfp_export,
        documents=wfp_documents,
        manifest=price_manifest,
    )

    with weather_path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in weather_rows:
            handle.write(json.dumps(row, separators=(",", ":")))
            handle.write("\n")
    weather_dates = [item for row in weather_rows for item in row["response"]["daily"]["time"]]
    weather_manifest = build_manifest(
        weather_path,
        source_name="legacy_open_meteo_replay",
        source_url="legacy-mongodb-export:bronze/open_meteo_daily",
        license_name="CC-BY-4.0",
        source_period_start=min(weather_dates),
        source_period_end=max(weather_dates),
    )
    write_manifest(weather_manifest, weather_path.with_suffix(".jsonl.manifest.json"))
    write_provenance(
        args.destination / "legacy_open_meteo_replay.provenance.json",
        dataset="cuaca_harian",
        source_export=args.weather_export,
        documents=weather_documents,
        manifest=weather_manifest,
    )

    print(
        json.dumps(
            {
                "price_snapshot": str(price_path),
                "price_rows": len(price_rows),
                "price_snapshot_id": price_manifest["snapshot_id"],
                "weather_snapshot": str(weather_path),
                "weather_envelopes": len(weather_rows),
                "weather_daily_rows": len(weather_dates),
                "weather_snapshot_id": weather_manifest["snapshot_id"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
