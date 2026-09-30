"""Bronze -> silver loader for silver.inflasi_kota (F3b).

Natural key: (bulan, kode_vervar).
"""

from __future__ import annotations

from typing import Any

from panganwatch.db import get_postgres_connection


def upsert_inflasi_kota(record: dict[str, Any], conn: Any = None) -> bool:
    """Upsert one row into silver.inflasi_kota. Returns True if it was a new insert."""
    owns_conn = conn is None
    conn = conn or get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO silver.inflasi_kota
                   (bulan, kode_vervar, nama_kota, ihk, inflasi_mtm, inflasi_yoy, source, run_id, loaded_at)
                   VALUES (%(bulan)s, %(kode_vervar)s, %(nama_kota)s, %(ihk)s, %(inflasi_mtm)s,
                           %(inflasi_yoy)s, %(source)s, %(run_id)s, now())
                   ON CONFLICT (bulan, kode_vervar)
                   DO UPDATE SET nama_kota = EXCLUDED.nama_kota, ihk = EXCLUDED.ihk,
                                 inflasi_mtm = EXCLUDED.inflasi_mtm, inflasi_yoy = EXCLUDED.inflasi_yoy,
                                 loaded_at = now()
                   RETURNING (xmax = 0) AS inserted""",
                record,
            )
            row = cur.fetchone()
        conn.commit()
        return bool(row[0]) if row else False
    finally:
        if owns_conn:
            conn.close()
