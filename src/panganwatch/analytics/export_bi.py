#!/usr/bin/env python3
"""
Export BI: write CSVs to exports/tableau/ for Tableau Public.

Files produced:
- fct_harga_harian.csv (period limited to keep it < 50MB)
- mart_disparitas_provinsi.csv
- mart_cuaca_harga_bulanan.csv
- mart_dq_scorecard.csv
- dim_provinsi.csv (with lat/lon for the map)
- dim_komoditas.csv
- mart_inflasi_vs_harga.csv (BPS city inflation vs. food price, F3b)
Every file has a header and UTF-8 encoding.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection


def export_csv(query, filename, conn):
    """Execute query and export to CSV."""
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

    import pandas as pd

    df = pd.DataFrame(rows, columns=cols)

    path = Path("exports/tableau") / filename
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  ✓ {filename}: {len(df)} rows, {path.stat().st_size:,} bytes")
    return df


def main():
    print("Exporting BI data to exports/tableau/...")

    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SET search_path TO gold, ref, governance, public")

    try:
        export_dir = Path("exports/tableau")
        export_dir.mkdir(parents=True, exist_ok=True)

        # 1. fct_harga_harian.csv (period limited to keep it < 50MB)
        print("\n1. fct_harga_harian.csv")
        export_csv(
            """
            SELECT tanggal, kode_provinsi_bps, komoditas_id, jenis_pasar, source,
                   harga_median, harga_min, harga_max, n_observasi, n_dq_warn
            FROM gold.fct_harga_bulanan
            WHERE tanggal >= '2025-06-01'
            ORDER BY tanggal, kode_provinsi_bps, komoditas_id, jenis_pasar, source
        """,
            "fct_harga_harian.csv",
            conn,
        )

        # 2. mart_disparitas_provinsi.csv
        print("\n2. mart_disparitas_provinsi.csv")
        export_csv(
            """
            SELECT bulan, kode_provinsi_bps, komoditas_id,
                   harga_median_provinsi, harga_median_nasional,
                   pct_deviasi, rank_deviasi
            FROM gold.mart_disparitas_provinsi
            ORDER BY bulan, kode_provinsi_bps, komoditas_id
        """,
            "mart_disparitas_provinsi.csv",
            conn,
        )

        # 3. mart_cuaca_harga_bulanan.csv
        print("\n3. mart_cuaca_harga_bulanan.csv")
        export_csv(
            """
            SELECT bulan, kode_provinsi_bps, kelompok,
                   hari_hujan_lebat, total_hujan_mm,
                   harga_median, pct_change_mom
            FROM gold.mart_cuaca_harga_bulanan
            ORDER BY bulan, kode_provinsi_bps, kelompok
        """,
            "mart_cuaca_harga_bulanan.csv",
            conn,
        )

        # 4. mart_dq_scorecard.csv
        print("\n4. mart_dq_scorecard.csv")
        export_csv(
            """
            SELECT source, dimensi, rules_total, rules_passed,
                   rows_checked, rows_failed, score
            FROM gold.mart_dq_scorecard
            ORDER BY source, dimensi
        """,
            "mart_dq_scorecard.csv",
            conn,
        )

        # 5. dim_provinsi.csv (with lat/lon for the map)
        print("\n5. dim_provinsi.csv")
        export_csv(
            """
            SELECT kode_bps AS kode_provinsi_bps, nama_provinsi, ibu_kota, lat, lon, kode_kemendagri
            FROM ref.ref_provinsi
            ORDER BY kode_bps
        """,
            "dim_provinsi.csv",
            conn,
        )

        # 6. dim_komoditas.csv
        print("\n6. dim_komoditas.csv")
        export_csv(
            """
            SELECT komoditas_id, nama_kanonis AS nama_komoditas, kelompok, satuan, het
            FROM ref.ref_komoditas
            ORDER BY komoditas_id
        """,
            "dim_komoditas.csv",
            conn,
        )

        # 7. mart_inflasi_vs_harga.csv (F3b: BPS city IHK/inflation vs. provincial food price)
        print("\n7. mart_inflasi_vs_harga.csv")
        export_csv(
            """
            SELECT bulan, kode_vervar, nama_kota, kode_provinsi_bps, nama_provinsi,
                   ihk, inflasi_mtm, inflasi_yoy, pct_change_harga_pangan, n_komoditas
            FROM gold.mart_inflasi_vs_harga
            ORDER BY bulan, kode_vervar
        """,
            "mart_inflasi_vs_harga.csv",
            conn,
        )

        # Verify all files < 50MB
        print("\n=== FILE SIZE VERIFICATION ===")
        all_ok = True
        for f in export_dir.glob("*.csv"):
            size_mb = f.stat().st_size / (1024 * 1024)
            status = "✓" if size_mb < 50 else "✗ > 50MB"
            print(f"  {status} {f.name}: {size_mb:.2f} MB")
            if size_mb >= 50:
                all_ok = False

        if all_ok:
            print("\n✓ All CSV files are < 50MB")
        else:
            print("\n⚠ Some files exceed 50MB")

        # Count files
        csv_files = list(export_dir.glob("*.csv"))
        print(f"\nTotal CSV files: {len(csv_files)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
