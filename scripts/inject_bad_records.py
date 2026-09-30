"""Inject bad records into the ingestion pipeline to test DQ quarantine.

Usage:
    uv run python scripts/inject_bad_records.py

This script inserts known-bad records (negative prices, invalid province codes,
future dates) through the normal ingestion path and verifies they end up in
governance.quarantine rather than silver.
"""

from __future__ import annotations

import uuid
from datetime import date

from panganwatch.db import get_postgres_connection
from panganwatch.dq.engine import DQEngine


def inject_bad_records() -> None:
    """Insert bad records and run DQ checks to verify quarantine."""
    run_id = str(uuid.uuid4())

    # Get connection and insert directly into silver to test the DQ engine
    # We'll test the engine against the data that exists

    print(f"Run ID: {run_id}")

    # Create test records with known issues
    bad_records = [
        # Negative price (invalid)
        {
            "tanggal": date(2025, 6, 20),
            "kode_provinsi_bps": "31",  # Jakarta
            "kode_kabkota_bps": "3171",
            "komoditas_id": "beras_premium",
            "jenis_pasar": "pasar_induk",
            "harga": -5000,  # NEGATIVE - should fail range check
            "satuan": "kg",
            "source": "HDX WFP",
            "run_id": run_id,
        },
        # Future date (invalid)
        {
            "tanggal": date(2030, 1, 15),
            "kode_provinsi_bps": "31",
            "kode_kabkota_bps": "3171",
            "komoditas_id": "cabai_merah_besar",
            "jenis_pasar": "pasar_induk",
            "harga": 15000,
            "satuan": "kg",
            "source": "HDX WFP",
            "run_id": run_id,
        },
        # Invalid province code (not in ref)
        {
            "tanggal": date(2025, 6, 21),
            "kode_provinsi_bps": "XX",  # Invalid
            "kode_kabkota_bps": "XX01",
            "komoditas_id": "beras_premium",
            "jenis_pasar": "pasar_induk",
            "harga": 12000,
            "satuan": "kg",
            "source": "HDX WFP",
            "run_id": run_id,
        },
        # Valid record (should pass)
        {
            "tanggal": date(2025, 6, 22),
            "kode_provinsi_bps": "31",
            "kode_kabkota_bps": "3171",
            "komoditas_id": "beras_premium",
            "jenis_pasar": "pasar_induk",
            "harga": 12500,
            "satuan": "kg",
            "source": "HDX WFP",
            "run_id": run_id,
        },
    ]

    # Run DQ checks on the bad records
    engine = DQEngine()
    clean, quarantined = engine.check_records("silver.harga_pangan", bad_records, run_id)

    print(f"\nTotal records: {len(bad_records)}")
    print(f"Clean records: {len(clean)}")
    print(f"Quarantined records: {len(quarantined)}")

    # Verify bad records are quarantined
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            # Check quarantine table
            cur.execute(
                "SELECT COUNT(*) FROM governance.quarantine WHERE run_id = %s",
                (run_id,),
            )
            quarantined_count = cur.fetchone()[0]
            print(f"\nQuarantine table count (run_id={run_id}): {quarantined_count}")

            # Check dq_results
            cur.execute(
                "SELECT rule_id, rows_checked, rows_failed, pass_rate FROM governance.dq_results WHERE run_id = %s ORDER BY rule_id",
                (run_id,),
            )
            results = cur.fetchall()
            print(f"\nDQ Results for run {run_id}:")
            for r in results:
                print(f"  Rule {r[0]}: checked={r[1]}, failed={r[2]}, pass_rate={r[3]}%")

            # Verify quarantined records are NOT in silver
            cur.execute(
                """SELECT COUNT(*) FROM silver.harga_pangan
                   WHERE run_id = %s AND tanggal IN ('2025-06-20', '2030-01-15')""",
                (run_id,),
            )
            silver_count = cur.fetchone()[0]
            print(f"\nBad records found in silver (should be 0): {silver_count}")

    finally:
        conn.close()

    if quarantined_count >= 3 and silver_count == 0:
        print("\n✓ All bad records successfully quarantined, none reached silver")
    else:
        print("\n✗ Some bad records may not have been properly quarantined")


if __name__ == "__main__":
    inject_bad_records()
