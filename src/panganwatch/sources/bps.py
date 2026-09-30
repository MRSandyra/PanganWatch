"""F3b: monthly consumer-price index (IHK) and inflation per city from the BPS WebAPI.

Variable ids were discovered through the API's own list endpoints, not
assumed: domain 0000 (Pusat), var 2245 "Indeks Harga Konsumen 150
Kabupaten/Kota (2022=100)" and var 2249 "Inflasi Tahunan (Y-on-Y) 150
Kabupaten/Kota (2022=100)". Month-to-month inflation is derived from consecutive
IHK values (BPS publishes no M-to-M variable for the 150-city basket).

`BPS_API_KEY` comes from .env and is NEVER printed or stored: URLs are logged
and stored without it, exceptions are scrubbed, only "SET"/"EMPTY" is shown.
With an empty key the job records a `skipped` governance.pipeline_runs row.

CLI: `uv run python -m panganwatch.sources.bps --run [--years 2025,2026]`
"""

from __future__ import annotations

import argparse
import math
import os
import time
import uuid
from datetime import date
from typing import Any

import httpx

from panganwatch.bronze import store_raw
from panganwatch.db import get_postgres_connection
from panganwatch.governance.pipeline_runs import finish_run, skip_run, start_run
from panganwatch.silver.inflasi_kota import upsert_inflasi_kota

SOURCE_NAME = "BPS"
BASE_URL = "https://webapi.bps.go.id/v1/api"
DOMAIN = "0000"
VAR_IHK = 2245
VAR_YOY = 2249
# Guard against silent variable-id drift: the payload's own label must match.
EXPECTED_LABEL = {
    VAR_IHK: "Indeks Harga Konsumen 150 Kabupaten/Kota",
    VAR_YOY: "Inflasi Tahunan (Y-on-Y) 150 Kabupaten/Kota",
}
MONGO_COLLECTION = "bps_inflation"
NATIONAL_LABEL = "INDONESIA"
REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 4
MONTHS = {
    "Januari": 1,
    "Februari": 2,
    "Maret": 3,
    "April": 4,
    "Mei": 5,
    "Juni": 6,
    "Juli": 7,
    "Agustus": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Desember": 12,
}


class BPSError(RuntimeError):
    """BPS returned an error status or an unexpected payload."""


class BPSRateLimitError(BPSError):
    """HTTP 429 — stop immediately, never retry (a politeness rule for external APIs)."""


def api_key_status() -> str:
    return "SET" if os.getenv("BPS_API_KEY") else "EMPTY"


def _scrub(text: str, key: str) -> str:
    return text.replace(key, "<KEY>") if key else text


def fetch_json(
    path: str, key: str, client: httpx.Client | None = None
) -> tuple[dict[str, Any], int]:
    """GET {BASE_URL}/{path}/key/<key>/ with delay, backoff on 5xx/transport errors, stop on 429."""
    url = f"{BASE_URL}/{path}/key/{key}/"
    own = client is None
    client = client or httpx.Client(
        headers={"User-Agent": "PanganWatch-portfolio/1.0 (+github)"}, timeout=60.0
    )
    try:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            time.sleep(REQUEST_DELAY_SECONDS)
            try:
                resp = client.get(url)
            except httpx.TransportError as exc:
                last_exc = BPSError(_scrub(f"transport error: {exc}", key))
            else:
                if resp.status_code == 429:
                    raise BPSRateLimitError("BPS returned HTTP 429; stopping (no retry)")
                if resp.status_code >= 500:
                    last_exc = BPSError(f"HTTP {resp.status_code} from BPS")
                else:
                    try:
                        body = resp.json()
                    except ValueError as exc:
                        raise BPSError(f"non-JSON response (HTTP {resp.status_code})") from exc
                    if resp.status_code >= 400 or body.get("status") != "OK":
                        msg = _scrub(str(body.get("message", body))[:200], key)
                        raise BPSError(f"BPS error (HTTP {resp.status_code}): {msg}")
                    return body, resp.status_code
            time.sleep(2**attempt)  # exponential backoff before the next attempt
        raise last_exc or BPSError("request failed")
    finally:
        if own:
            client.close()


def list_years(key: str, client: httpx.Client | None = None) -> list[int]:
    """Available period ids (th_id, = year - 1900) for the IHK variable."""
    body, _ = fetch_json(f"list/model/th/domain/{DOMAIN}/var/{VAR_IHK}", key, client)
    rows = body["data"][1]
    return sorted(int(r["th_id"]) for r in rows)


def fetch_data(
    var: int, th_id: int, key: str, client: httpx.Client | None = None
) -> dict[str, Any]:
    body, _ = fetch_json(f"list/model/data/domain/{DOMAIN}/var/{var}/th/{th_id}", key, client)
    label = body["var"][0]["label"]
    if EXPECTED_LABEL[var] not in label:
        raise BPSError(f"variable {var} label drifted: {label!r}")
    return body


def parse_data(payload: dict[str, Any], var: int) -> list[dict[str, Any]]:
    """Pure: BPS data payload -> [{kode_vervar, nama_kota, bulan, value}].

    datacontent keys are the concatenation vervar + var + turvar + tahun + turtahun.
    Only the 12 monthly turtahun entries are read (the 13th is the annual value).
    """
    turvar = str(payload["turvar"][0]["val"])
    th_id = str(payload["tahun"][0]["val"])
    year = int(th_id) + 1900
    months = [(t["val"], MONTHS[t["label"]]) for t in payload["turtahun"] if t["label"] in MONTHS]
    content = payload["datacontent"]
    out: list[dict[str, Any]] = []
    for v in payload["vervar"]:
        for tt, month in months:
            cell = f"{v['val']}{var}{turvar}{th_id}{tt}"
            if cell not in content:
                continue
            out.append(
                {
                    "kode_vervar": int(v["val"]),
                    "nama_kota": str(v["label"]).strip(),
                    "bulan": date(year, month, 1),
                    "value": content[cell],
                }
            )
    return out


def _to_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _previous_month(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def compute_records(
    ihk_cells: list[dict[str, Any]], yoy_cells: list[dict[str, Any]], run_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Pure: merge IHK + Y-on-Y cells into silver records, deriving M-to-M from IHK.

    Returns (records, quarantined_cells, national_rows_skipped). The national
    aggregate (INDONESIA) is not a city and is skipped; cells whose IHK is not
    a finite number are quarantined, never silently dropped.
    """
    yoy = {(c["kode_vervar"], c["bulan"]): _to_float(c["value"]) for c in yoy_cells}
    ihk: dict[tuple[int, date], float] = {}
    names: dict[int, str] = {}
    quarantined: list[dict[str, Any]] = []
    national = 0
    for c in ihk_cells:
        if c["nama_kota"].upper() == NATIONAL_LABEL:
            national += 1
            continue
        value = _to_float(c["value"])
        if value is None:
            quarantined.append(c)
            continue
        ihk[(c["kode_vervar"], c["bulan"])] = value
        names[c["kode_vervar"]] = c["nama_kota"]

    records = []
    for (vervar, bulan), value in sorted(ihk.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        prev = ihk.get((vervar, _previous_month(bulan)))
        mtm = round((value / prev - 1) * 100, 2) if prev else None
        records.append(
            {
                "bulan": bulan,
                "kode_vervar": vervar,
                "nama_kota": names[vervar],
                "ihk": round(value, 2),
                "inflasi_mtm": mtm,
                "inflasi_yoy": yoy.get((vervar, bulan)),
                "source": SOURCE_NAME,
                "run_id": run_id,
            }
        )
    return records, quarantined, national


def run_ingestion(
    run_id: str, key: str, years: list[int] | None = None
) -> tuple[int, int, int, int]:
    """Fetch, store raw (bronze), and load (silver). Returns (fetched, loaded, quarantined, national_skipped)."""
    client = httpx.Client(
        headers={"User-Agent": "PanganWatch-portfolio/1.0 (+github)"}, timeout=60.0
    )
    try:
        th_ids = years or list_years(key, client)
        ihk_cells: list[dict[str, Any]] = []
        yoy_cells: list[dict[str, Any]] = []
        for th_id in th_ids:
            for var, sink in ((VAR_IHK, ihk_cells), (VAR_YOY, yoy_cells)):
                payload = fetch_data(var, th_id, key, client)
                store_raw(
                    source="bps_inflation",
                    endpoint=f"{BASE_URL}/list/model/data/domain/{DOMAIN}/var/{var}/th/{th_id}",
                    params={"domain": DOMAIN, "var": var, "th": th_id},
                    payload=payload,
                    http_status=200,
                    run_id=run_id,
                    collection=MONGO_COLLECTION,
                )
                sink.extend(parse_data(payload, var))
    finally:
        client.close()

    records, quarantined, national = compute_records(ihk_cells, yoy_cells, run_id)
    conn = get_postgres_connection()
    try:
        for record in records:
            upsert_inflasi_kota(record, conn=conn)
    finally:
        conn.close()
    return len(records) + len(quarantined), len(records), len(quarantined), national


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m panganwatch.sources.bps",
        description="Ingest IHK/inflation per city from BPS WebAPI into bronze/silver (F3b); skips cleanly if BPS_API_KEY is empty.",
    )
    p.add_argument(
        "--run", action="store_true", help="Run the job (or record a skip if no API key)"
    )
    p.add_argument(
        "--years",
        type=str,
        default=None,
        help="Comma-separated calendar years to fetch (default: every year BPS lists)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    status = api_key_status()
    print(f"[BPS] BPS_API_KEY={status}")

    if not args.run:
        build_arg_parser().print_help()
        return 0

    run_id = str(uuid.uuid4())
    if status == "EMPTY":
        reason = "BPS_API_KEY is empty in .env; F3b is skipped by design (see docs/handover.md #1)."
        skip_run(run_id, SOURCE_NAME, reason)
        print(f"[BPS] skipped run_id={run_id}: {reason}")
        return 0

    key = os.environ["BPS_API_KEY"]
    years = [int(y) - 1900 for y in args.years.split(",")] if args.years else None
    start_run(run_id, SOURCE_NAME)
    try:
        fetched, loaded, quarantined, national = run_ingestion(run_id, key, years)
    except BPSError as exc:
        msg = _scrub(str(exc), key)
        finish_run(run_id, SOURCE_NAME, "failed", error_message=msg)
        print(f"[BPS] run_id={run_id} FAILED: {msg}")
        return 2
    except Exception as exc:  # never leak the key through unexpected errors
        msg = _scrub(f"{type(exc).__name__}: {exc}", key)
        finish_run(run_id, SOURCE_NAME, "failed", error_message=msg)
        print(f"[BPS] run_id={run_id} FAILED: {msg}")
        return 2

    finish_run(
        run_id,
        SOURCE_NAME,
        "success" if quarantined == 0 else "partial",
        rows_fetched=fetched,
        rows_loaded=loaded,
        rows_quarantined=quarantined,
    )
    print(
        f"[BPS] run_id={run_id} fetched={fetched} loaded={loaded} quarantined={quarantined} "
        f"national_skipped={national} status={'success' if quarantined == 0 else 'partial'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
