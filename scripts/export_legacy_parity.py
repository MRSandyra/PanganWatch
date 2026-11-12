"""Export a read-only legacy Silver slice as JSONL for cloud comparison."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SELECTS = {
    "harga_pangan": """
        SELECT tanggal, kode_provinsi_bps, kode_kabkota_bps, komoditas_id,
               jenis_pasar, harga, satuan, source
        FROM silver.harga_pangan
    """,
    "cuaca_harian": """
        SELECT tanggal, kode_provinsi_bps, precipitation_mm, tmax_c, tmin_c, source
        FROM silver.cuaca_harian
    """,
}


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected YYYY-MM-DD, received {value!r}") from exc


def main() -> int:
    from panganwatch.db import get_postgres_connection

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Restored comparison database name")
    parser.add_argument("--dataset", required=True, choices=sorted(SELECTS))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start-date", type=parse_date)
    parser.add_argument("--end-date", type=parse_date)
    parser.add_argument("--source", help="Optional source value used to select legacy rows")
    parser.add_argument(
        "--canonical-source",
        help="Optional source label written to every exported row after source selection",
    )
    args = parser.parse_args()

    if args.start_date and args.end_date and args.start_date > args.end_date:
        parser.error("--start-date must not be after --end-date")
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing export: {args.output}")

    predicates: list[str] = []
    parameters: list[Any] = []
    if args.start_date:
        predicates.append("tanggal >= %s")
        parameters.append(args.start_date)
    if args.end_date:
        predicates.append("tanggal <= %s")
        parameters.append(args.end_date)
    if args.source:
        predicates.append("source = %s")
        parameters.append(args.source)
    query = SELECTS[args.dataset]
    if predicates:
        query += " WHERE " + " AND ".join(predicates)
    query += " ORDER BY tanggal, kode_provinsi_bps"

    # The project .env is intentionally loaded by panganwatch.db. Override only
    # the database name after that load so this script cannot touch the active
    # newly initialized database by accident.
    os.environ["POSTGRES_DB"] = args.database
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters)
            columns = [item.name for item in cursor.description]
            rows = [dict(zip(columns, row, strict=True)) for row in cursor]
    finally:
        conn.close()

    if not rows:
        raise ValueError("No rows matched the requested dataset, source, and date interval")

    if args.canonical_source:
        for row in rows:
            row["source"] = args.canonical_source

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, default=str, sort_keys=True))
            handle.write("\n")

    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "database": args.database,
                "rows": len(rows),
                "first_date": str(rows[0]["tanggal"]),
                "last_date": str(rows[-1]["tanggal"]),
                "output": str(args.output),
                "canonical_source": args.canonical_source,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
