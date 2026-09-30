#!/usr/bin/env python3
"""
Analytics: price disparity per province vs. the national median.

Computes, for each commodity:
1. The province with the largest average deviation from the national median (last 90 days)
2. The coefficient of variation (CV) across provinces, per week
"""

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection


def get_gold_connection():
    """Get connection and set search_path to gold schema."""
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SET search_path TO gold, public")
    return conn


def load_mart_disparitas(conn, days_back=90):
    """Load mart_disparitas_provinsi for last N days."""
    with conn.cursor() as cur:
        # Get max date first
        cur.execute("""
            SELECT max(bulan) FROM gold.mart_disparitas_provinsi
        """)
        max_date = cur.fetchone()[0]
        if max_date is None:
            return pd.DataFrame()

        start_date = max_date - timedelta(days=days_back)

        cur.execute(
            """
            SELECT
                bulan as tanggal,
                kode_provinsi_bps,
                komoditas_id,
                harga_median_provinsi,
                harga_median_nasional,
                pct_deviasi,
                rank_deviasi
            FROM gold.mart_disparitas_provinsi
            WHERE bulan >= %s
            ORDER BY bulan, komoditas_id, kode_provinsi_bps
        """,
            (start_date,),
        )
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def compute_summary(df):
    """Compute summary statistics per komoditas."""
    if df.empty:
        return pd.DataFrame()

    results = []

    for komoditas_id, group in df.groupby("komoditas_id"):
        # Average deviation per province over the period
        avg_dev = group.groupby("kode_provinsi_bps")["pct_deviasi"].mean().reset_index()
        avg_dev.columns = ["kode_provinsi_bps", "avg_pct_deviasi"]

        # Province with max average deviation (absolute)
        max_dev_row = avg_dev.loc[avg_dev["avg_pct_deviasi"].abs().idxmax()]

        # Weekly coefficient of variation across provinces
        # Group by week (ISO week) and komoditas
        df_weekly = group.copy()
        df_weekly["tanggal"] = pd.to_datetime(df_weekly["tanggal"])
        df_weekly["week"] = df_weekly["tanggal"].dt.isocalendar().week
        df_weekly["year"] = df_weekly["tanggal"].dt.isocalendar().year
        df_weekly["year_week"] = (
            df_weekly["year"].astype(str) + "-W" + df_weekly["week"].astype(str).str.zfill(2)
        )

        weekly_cv = (
            df_weekly.groupby("year_week")["harga_median_provinsi"]
            .agg(mean="mean", std="std", count="count")
            .reset_index()
        )
        weekly_cv["cv_pct"] = (weekly_cv["std"] / weekly_cv["mean"] * 100).round(2)
        weekly_cv["komoditas_id"] = komoditas_id

        avg_cv = weekly_cv["cv_pct"].mean()

        results.append(
            {
                "komoditas_id": komoditas_id,
                "provinsi_max_deviasi": max_dev_row["kode_provinsi_bps"],
                "avg_pct_deviasi_max": round(max_dev_row["avg_pct_deviasi"], 2),
                "avg_weekly_cv_pct": round(avg_cv, 2),
                "n_weeks": len(weekly_cv),
                "n_provinces": group["kode_provinsi_bps"].nunique(),
                "period_start": group["tanggal"].min(),
                "period_end": group["tanggal"].max(),
            }
        )

    return pd.DataFrame(results)


def compute_weekly_cv_detail(df):
    """Compute detailed weekly CV per komoditas per week."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["week"] = df["tanggal"].dt.isocalendar().week
    df["year"] = df["tanggal"].dt.isocalendar().year
    df["year_week"] = df["year"].astype(str) + "-W" + df["week"].astype(str).str.zfill(2)

    detail = (
        df.groupby(["komoditas_id", "year_week"])["harga_median_provinsi"]
        .agg(mean="mean", std="std", count="count")
        .reset_index()
    )
    detail["cv_pct"] = (detail["std"] / detail["mean"] * 100).round(2)
    detail = detail[["komoditas_id", "year_week", "mean", "std", "count", "cv_pct"]]
    detail.columns = [
        "komoditas_id",
        "year_week",
        "mean_harga_median",
        "std_harga_median",
        "n_provinsi",
        "cv_pct",
    ]

    return detail


def main():
    print("Loading mart_disparitas_provinsi from gold schema...")
    conn = get_gold_connection()
    try:
        df = load_mart_disparitas(conn, days_back=90)
        print(f"Loaded {len(df)} rows from mart_disparitas_provinsi")

        if df.empty:
            print("No data found. Skipping.")
            return

        # Compute summary
        summary = compute_summary(df)
        weekly_detail = compute_weekly_cv_detail(df)

        # Print results
        print("\n=== SUMMARY PER COMMODITY (last 90 days) ===")
        for _, row in summary.iterrows():
            print(f"Commodity: {row['komoditas_id']}")
            print(
                f"  Province with max deviation: {row['provinsi_max_deviasi']} ({row['avg_pct_deviasi_max']:+.2f}%)"
            )
            print(f"  Avg weekly CV: {row['avg_weekly_cv_pct']:.2f}%")
            print(
                f"  Period: {row['period_start']} to {row['period_end']} ({row['n_weeks']} weeks, {row['n_provinces']} provinces)"
            )

        print("\n=== WEEKLY CV DETAIL (sample) ===")
        print(weekly_detail.head(20).to_string(index=False))

        # Save to exports for Tableau
        export_dir = Path("exports/tableau")
        export_dir.mkdir(parents=True, exist_ok=True)

        summary_path = export_dir / "mart_disparitas_summary.csv"
        summary.to_csv(summary_path, index=False, encoding="utf-8")
        print(f"\nSaved summary to {summary_path}")

        weekly_path = export_dir / "mart_disparitas_weekly_cv.csv"
        weekly_detail.to_csv(weekly_path, index=False, encoding="utf-8")
        print(f"Saved weekly CV detail to {weekly_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
