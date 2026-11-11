"""Freeze reproducible Open-Meteo Archive responses for the PanganWatch provinces."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from databricks.src.manifest import build_manifest, write_manifest  # noqa: E402

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = "precipitation_sum,temperature_2m_max,temperature_2m_min"
SEED_PATH = PROJECT_ROOT / "dbt" / "panganwatch" / "seeds" / "ref_provinsi.csv"


def read_provinces(path: Path = SEED_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def date_chunks(start: date, end: date, days: int):
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def groups(values: list[dict[str, str]], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def fetch_json(params: dict[str, str], *, pause_seconds: float, attempts: int) -> list[dict]:
    for attempt in range(1, attempts + 1):
        request = Request(
            f"{ARCHIVE_URL}?{urlencode(params)}",
            headers={"User-Agent": "PanganWatch/2.0 (frozen research snapshot)"},
        )
        try:
            with urlopen(request, timeout=120) as response:  # noqa: S310 - fixed HTTPS API endpoint
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(f"Open-Meteo returned an error: {payload.get('reason', payload)}")
            return payload if isinstance(payload, list) else [payload]
        except HTTPError as error:
            if error.code != 429 or attempt == attempts:
                raise
            try:
                retry_after = float(error.headers.get("Retry-After", ""))
            except ValueError:
                retry_after = 0
            time.sleep(max(pause_seconds, retry_after, 2**attempt))
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--chunk-days", type=int, default=366)
    parser.add_argument("--locations-per-request", type=int, default=5)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--max-attempts", type=int, default=6)
    args = parser.parse_args()
    if args.start_date > args.end_date:
        raise ValueError("--start-date must not be after --end-date")
    if args.chunk_days < 1:
        raise ValueError("--chunk-days must be at least 1")
    if args.locations_per_request < 1:
        raise ValueError("--locations-per-request must be at least 1")
    if args.pause_seconds < 0:
        raise ValueError("--pause-seconds must not be negative")
    if args.max_attempts < 1:
        raise ValueError("--max-attempts must be at least 1")
    if args.destination.exists():
        raise FileExistsError(f"Refusing to overwrite immutable snapshot: {args.destination}")
    partial_path = args.destination.with_name(f"{args.destination.name}.partial")
    if partial_path.exists():
        raise FileExistsError(
            f"Partial snapshot exists after an interrupted attempt: {partial_path}. "
            "Inspect it, then remove it before retrying."
        )

    provinces = read_provinces()
    if len(provinces) != 38:
        raise ValueError(f"Expected 38 committed province seeds, found {len(provinces)}")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    response_count = 0
    with partial_path.open("x", encoding="utf-8") as output:
        for chunk_start, chunk_end in date_chunks(args.start_date, args.end_date, args.chunk_days):
            for province_group in groups(provinces, args.locations_per_request):
                params = {
                    "latitude": ",".join(province["lat"] for province in province_group),
                    "longitude": ",".join(province["lon"] for province in province_group),
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "daily": DAILY_FIELDS,
                    "timezone": "Asia/Jakarta",
                    "models": "era5",
                }
                responses = fetch_json(
                    params, pause_seconds=args.pause_seconds, attempts=args.max_attempts
                )
                if len(responses) != len(province_group):
                    raise RuntimeError(
                        f"Expected {len(province_group)} API responses for {chunk_start}..{chunk_end}, got {len(responses)}"
                    )
                for province, response in zip(province_group, responses, strict=True):
                    output.write(
                        json.dumps(
                            {
                                "requested_province": {
                                    "kode_provinsi_bps": province["kode_bps"],
                                    "nama_provinsi": province["nama_provinsi"],
                                },
                                "request": params,
                                "response": response,
                            },
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    response_count += 1
                time.sleep(args.pause_seconds)

    partial_path.replace(args.destination)

    manifest = build_manifest(
        args.destination,
        source_name="open_meteo",
        source_url=ARCHIVE_URL,
        license_name="CC-BY-4.0",
        source_period_start=args.start_date.isoformat(),
        source_period_end=args.end_date.isoformat(),
    )
    manifest_path = write_manifest(
        manifest, args.destination.with_suffix(args.destination.suffix + ".manifest.json")
    )
    print(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot_id"],
                "responses": response_count,
                "snapshot": str(args.destination),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
