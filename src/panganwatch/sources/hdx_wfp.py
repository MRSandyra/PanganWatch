"""F3a: food price ingestion from the HDX "Indonesia - Food Prices" dataset (WFP).

Used because PIHPS / Panel Harga Badan Pangan is not viably scrapable within
this project's constraints (3 approaches were tried and failed):
panelharga.badanpangan.go.id was in maintenance and its `/api/harga` route
falls through to the SPA shell rather than JSON; the legacy
bi.go.id/hargapangan panel requires an ASP.NET session with an anti-forgery
token, not a plain polite GET.

Dataset: World Food Programme, "Indonesia - Food Prices" on HDX.
Landing page: https://data.humdata.org/dataset/wfp-food-prices-for-indonesia
CSV resource discovered via the HDX CKAN API (package_show).

The backfill window is derived from the dataset's own max date (not
datetime.now()): the CSV's most recent rows set the end of the window, and
`--backfill-days` (default from config/settings.yaml) sets how far back it
goes.

CLI: `uv run python -m panganwatch.sources.hdx_wfp --backfill`
"""

from __future__ import annotations

import argparse
import csv
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from panganwatch.bronze import store_raw
from panganwatch.config import get_settings
from panganwatch.db import get_postgres_connection
from panganwatch.governance.pipeline_runs import finish_run, start_run
from panganwatch.silver.harga_pangan import upsert_harga_pangan
from panganwatch.unmapped import append_unmapped

SOURCE_NAME = "HDX WFP"
MONGO_COLLECTION = "hdx_wfp_prices"

DATASET_LANDING_PAGE = "https://data.humdata.org/dataset/wfp-food-prices-for-indonesia"
RESOURCE_URL = (
    "https://data.humdata.org/dataset/72cc0659-142b-41af-821a-cb981a852617/"
    "resource/2c0e732c-1d93-4366-8f19-0397064ac5d7/download/wfp_food_prices_idn.csv"
)
ROOT = Path(__file__).resolve().parents[3]
RAW_CACHE = ROOT / "data" / "raw" / "wfp_food_prices_idn.csv"


def download_csv(force: bool = False, dest: Path = RAW_CACHE) -> Path:
    """Download the WFP CSV resource, caching it locally. Politeness: this is a
    single direct file download from HDX's CDN, not repeated page scraping."""
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "PanganWatch-portfolio/1.0 (+github)"}
    with httpx.stream(
        "GET", RESOURCE_URL, timeout=60.0, headers=headers, follow_redirects=True
    ) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return dest


def find_date_range(csv_path: Path) -> tuple[date, date]:
    """Scan the CSV once to find its actual min/max `date` values."""
    min_d: date | None = None
    max_d: date | None = None
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if min_d is None or d < min_d:
                min_d = d
            if max_d is None or d > max_d:
                max_d = d
    if min_d is None or max_d is None:
        raise ValueError(f"No rows with a parseable date in {csv_path}")
    return min_d, max_d


def normalize(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_province_mapping() -> dict[str, str]:
    """HDX admin1 string (as literally seen in the raw CSV) -> kode_bps."""
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nama_sumber, kode_bps FROM ref.ref_provinsi_alias WHERE sumber = 'HDX'"
            )
            return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()


def load_commodity_mapping() -> dict[str, str]:
    """HDX commodity string (as literally seen in the raw CSV) -> komoditas_id."""
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nama_sumber, komoditas_id FROM ref.ref_komoditas_alias WHERE sumber = 'HDX'"
            )
            return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()


def parse_and_map_row(
    row: dict[str, str],
    province_map: dict[str, str],
    commodity_map: dict[str, str],
) -> tuple[dict[str, Any] | None, str | None]:
    """Map one raw WFP CSV row to a silver.harga_pangan record.

    Pure function (no I/O) so it's covered by an offline unit test. Returns
    (record, None) on success or (None, reason) when the row can't be mapped
    (goes to data/tmp/unmapped_<run_id>.jsonl instead of silver).
    """
    admin1 = (row.get("admin1") or "").strip()
    kode_provinsi_bps = province_map.get(admin1)
    if not kode_provinsi_bps:
        # Generic normalized fallback in case a new admin1 spelling shows up
        # that isn't in the ref_provinsi_alias seed yet.
        norm = normalize(admin1) if admin1 else ""
        for src_name, kode in province_map.items():
            if normalize(src_name) == norm and norm:
                kode_provinsi_bps = kode
                break
    if not kode_provinsi_bps:
        return None, f"province not mapped: {admin1!r}"

    commodity = (row.get("commodity") or "").strip()
    komoditas_id = commodity_map.get(commodity)
    if not komoditas_id:
        return None, f"commodity not mapped: {commodity!r}"

    try:
        harga = float(row["price"])
    except (TypeError, ValueError, KeyError):
        return None, f"invalid price: {row.get('price')!r}"
    if harga <= 0:
        return None, f"non-positive price: {harga}"

    unit = (row.get("unit") or "KG").strip() or "KG"
    market = (row.get("market") or "Unknown").strip() or "Unknown"

    return (
        {
            "tanggal": row["date"],
            "kode_provinsi_bps": kode_provinsi_bps,
            "kode_kabkota_bps": None,
            "komoditas_id": komoditas_id,
            "jenis_pasar": market,
            "harga": harga,
            "satuan": f"rupiah/{unit}",
            "source": SOURCE_NAME,
        },
        None,
    )


def run_ingestion(
    csv_path: Path, start_date: date, end_date: date, run_id: str
) -> tuple[int, int, int]:
    """Filter rows to [start_date, end_date], map + upsert to silver, store raw
    rows to bronze in monthly chunks. Returns (rows_fetched, rows_loaded, rows_quarantined)."""
    province_map = load_province_mapping()
    commodity_map = load_commodity_mapping()

    monthly_raw: dict[str, list[dict[str, str]]] = defaultdict(list)
    rows_fetched = 0
    rows_loaded = 0
    rows_quarantined = 0

    conn = get_postgres_connection()
    try:
        with csv_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                except (ValueError, KeyError):
                    continue
                if d < start_date or d > end_date:
                    continue

                rows_fetched += 1
                monthly_raw[d.strftime("%Y-%m")].append(row)

                record, reason = parse_and_map_row(row, province_map, commodity_map)
                if record is None:
                    append_unmapped(run_id, MONGO_COLLECTION, row, reason or "unknown")
                    rows_quarantined += 1
                    continue

                record["run_id"] = run_id
                upsert_harga_pangan(record, conn=conn)
                rows_loaded += 1
    finally:
        conn.close()

    for year_month, rows in monthly_raw.items():
        store_raw(
            source="hdx_wfp",
            endpoint=RESOURCE_URL,
            params={"month": year_month, "start_date": str(start_date), "end_date": str(end_date)},
            payload=rows,
            http_status=200,
            run_id=run_id,
            collection=MONGO_COLLECTION,
        )

    return rows_fetched, rows_loaded, rows_quarantined


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m panganwatch.sources.hdx_wfp",
        description="Ingest Indonesian food prices from the HDX WFP dataset into bronze/silver (F3a).",
    )
    p.add_argument("--backfill", action="store_true", help="Run the backfill ingestion")
    p.add_argument(
        "--start-date", type=str, default=None, help="Override window start (YYYY-MM-DD)"
    )
    p.add_argument("--end-date", type=str, default=None, help="Override window end (YYYY-MM-DD)")
    p.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help="Days before the dataset's max date to backfill (default: config/settings.yaml ingestion.backfill_days)",
    )
    p.add_argument(
        "--csv-path", type=str, default=None, help="Use a local CSV instead of the downloaded cache"
    )
    p.add_argument(
        "--force-download", action="store_true", help="Re-download even if a local cache exists"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.backfill:
        build_arg_parser().print_help()
        return 0

    settings = get_settings()
    csv_path = Path(args.csv_path) if args.csv_path else download_csv(force=args.force_download)

    min_date, max_date = find_date_range(csv_path)
    backfill_days = args.backfill_days or settings.ingestion["backfill_days"]

    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else max_date
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date
        else max(min_date, end_date - timedelta(days=backfill_days))
    )

    run_id = str(uuid.uuid4())
    start_run(run_id, SOURCE_NAME)
    print(
        f"[HDX WFP] run_id={run_id} window={start_date}..{end_date} (dataset spans {min_date}..{max_date})"
    )

    try:
        rows_fetched, rows_loaded, rows_quarantined = run_ingestion(
            csv_path, start_date, end_date, run_id
        )
    except Exception as exc:  # noqa: BLE001
        finish_run(run_id, SOURCE_NAME, "failed", error_message=str(exc))
        print(f"[HDX WFP] FAILED: {exc}")
        raise

    status = "success" if rows_quarantined == 0 else "partial"
    finish_run(run_id, SOURCE_NAME, status, rows_fetched, rows_loaded, rows_quarantined)
    print(
        f"[HDX WFP] done: fetched={rows_fetched} loaded={rows_loaded} "
        f"quarantined={rows_quarantined} status={status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
