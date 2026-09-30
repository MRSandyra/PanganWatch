"""Bronze -> silver loader for silver.harga_pangan (F3a).

Natural key: (tanggal, kode_provinsi_bps, coalesce(kode_kabkota_bps,''),
komoditas_id, jenis_pasar, source) - enforced by a unique expression index
(sql/ddl/init_governance.sql), so upserts are idempotent.
"""

from __future__ import annotations

from typing import Any

from panganwatch.db import get_postgres_connection


def upsert_harga_pangan(record: dict[str, Any], conn: Any = None) -> bool:
    """Upsert one row into silver.harga_pangan. Returns True if it was a new insert.

    Pass `conn` to reuse a connection across many calls (a fresh connection
    per row is too slow for backfills of thousands of rows).
    """
    owns_conn = conn is None
    conn = conn or get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO silver.harga_pangan
                   (tanggal, kode_provinsi_bps, kode_kabkota_bps, komoditas_id, jenis_pasar,
                    harga, satuan, source, run_id, loaded_at)
                   VALUES (%(tanggal)s, %(kode_provinsi_bps)s, %(kode_kabkota_bps)s, %(komoditas_id)s,
                           %(jenis_pasar)s, %(harga)s, %(satuan)s, %(source)s, %(run_id)s, now())
                   ON CONFLICT (tanggal, kode_provinsi_bps, COALESCE(kode_kabkota_bps, ''),
                                komoditas_id, jenis_pasar, source)
                   DO UPDATE SET harga = EXCLUDED.harga, satuan = EXCLUDED.satuan, loaded_at = now()
                   RETURNING (xmax = 0) AS inserted""",
                record,
            )
            row = cur.fetchone()
        conn.commit()
        return bool(row[0]) if row else False
    finally:
        if owns_conn:
            conn.close()


def count_harga_pangan(source: str | None = None) -> int:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            if source:
                cur.execute("SELECT count(*) FROM silver.harga_pangan WHERE source = %s", (source,))
            else:
                cur.execute("SELECT count(*) FROM silver.harga_pangan")
            return cur.fetchone()[0]
    finally:
        conn.close()
