"""Bronze -> silver loader for silver.cuaca_harian (F3c).

Natural key: (tanggal, kode_provinsi_bps).
"""

from __future__ import annotations

from typing import Any

from panganwatch.db import get_postgres_connection


def upsert_cuaca_harian(record: dict[str, Any], conn: Any = None) -> bool:
    """Upsert one row into silver.cuaca_harian. Returns True if it was a new insert.

    Pass `conn` to reuse a connection across many calls (a fresh connection
    per row is too slow for backfills of thousands of rows).
    """
    owns_conn = conn is None
    conn = conn or get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO silver.cuaca_harian
                   (tanggal, kode_provinsi_bps, precipitation_mm, tmax_c, tmin_c, source, run_id, loaded_at)
                   VALUES (%(tanggal)s, %(kode_provinsi_bps)s, %(precipitation_mm)s, %(tmax_c)s,
                           %(tmin_c)s, %(source)s, %(run_id)s, now())
                   ON CONFLICT (tanggal, kode_provinsi_bps)
                   DO UPDATE SET precipitation_mm = EXCLUDED.precipitation_mm,
                                 tmax_c = EXCLUDED.tmax_c, tmin_c = EXCLUDED.tmin_c, loaded_at = now()
                   RETURNING (xmax = 0) AS inserted""",
                record,
            )
            row = cur.fetchone()
        conn.commit()
        return bool(row[0]) if row else False
    finally:
        if owns_conn:
            conn.close()


def count_provinces_covered() -> int:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(DISTINCT kode_provinsi_bps) FROM silver.cuaca_harian")
            return cur.fetchone()[0]
    finally:
        conn.close()
