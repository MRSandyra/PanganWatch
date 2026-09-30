#!/usr/bin/env python3
"""Analytics: city inflation (BPS IHK) vs. provincial food-price change (F3b -> F9).

Source: gold.mart_inflasi_vs_harga (month x city). Food prices (HDX WFP) only
exist per province, so cities in the same province share the SAME
pct_change_harga_pangan value. To avoid counting the same observation
multiple times (pseudo-replication), city inflation is averaged to
province x month before the Spearman correlation is computed.

This is a CORRELATION, not causation: both are affected by harvest season,
holidays, policy, and fuel prices. pct_change_harga_pangan covers only 8 food
commodities, while the IHK covers the whole consumption basket (food is only
part of it).

Output (exports/tableau/): inflation_food_overall.csv, inflation_food_by_month.csv,
inflation_food_monthly.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection

EXPORT_DIR = Path("exports/tableau")
MIN_PAIRS = 6


def load_mart(conn) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT bulan, kode_vervar, nama_kota, kode_provinsi_bps, ihk, inflasi_mtm,
                      inflasi_yoy, pct_change_harga_pangan
               FROM gold.mart_inflasi_vs_harga ORDER BY bulan, kode_vervar"""
        )
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("ihk", "inflasi_mtm", "inflasi_yoy", "pct_change_harga_pangan"):
        df[c] = pd.to_numeric(df[c])
    return df


def province_month(df: pd.DataFrame) -> pd.DataFrame:
    """Average city inflation to province x month (one observation per province-month)."""
    paired = df.dropna(subset=["pct_change_harga_pangan", "inflasi_mtm"])
    return (
        paired.groupby(["bulan", "kode_provinsi_bps"], as_index=False)
        .agg(
            n_kota=("kode_vervar", "nunique"),
            inflasi_mtm=("inflasi_mtm", "mean"),
            inflasi_yoy=("inflasi_yoy", "mean"),
            pct_change_harga_pangan=("pct_change_harga_pangan", "first"),
        )
        .sort_values(["bulan", "kode_provinsi_bps"])
    )


def spearman(x: pd.Series, y: pd.Series) -> dict:
    n = len(x)
    if n < MIN_PAIRS or x.nunique() < 2 or y.nunique() < 2:
        return {"n": n, "rho": None, "p_value": None}
    rho, p = stats.spearmanr(x, y)
    return {"n": n, "rho": round(float(rho), 4), "p_value": round(float(p), 6)}


def analyze(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pm = province_month(df)
    overall_rows = []
    for label, xcol in (("inflasi_mtm vs pct_change_harga_pangan", "inflasi_mtm"),):
        overall_rows.append(
            {
                "pasangan": label,
                "unit": "provinsi x bulan",
                **spearman(pm[xcol], pm["pct_change_harga_pangan"]),
            }
        )
    # same, excluding the partial Jan/Feb-2026 months (only 8 provinces have prices)
    full = pm[~pm["bulan"].astype(str).isin(["2026-01-01", "2026-02-01"])]
    overall_rows.append(
        {
            "pasangan": "inflasi_mtm vs pct_change_harga_pangan (tanpa Jan-Feb 2026)",
            "unit": "provinsi x bulan",
            **spearman(full["inflasi_mtm"], full["pct_change_harga_pangan"]),
        }
    )

    by_month = []
    for bulan, g in pm.groupby("bulan"):
        s = spearman(g["inflasi_mtm"], g["pct_change_harga_pangan"])
        by_month.append(
            {
                "bulan": bulan,
                "n_provinsi": s["n"],
                "spearman_rho": s["rho"],
                "p_value": s["p_value"],
            }
        )

    monthly = (
        pm.groupby("bulan", as_index=False)
        .agg(
            n_provinsi=("kode_provinsi_bps", "nunique"),
            avg_inflasi_mtm=("inflasi_mtm", "mean"),
            avg_inflasi_yoy=("inflasi_yoy", "mean"),
            avg_pct_change_harga_pangan=("pct_change_harga_pangan", "mean"),
        )
        .round(3)
    )
    ts = spearman(monthly["avg_inflasi_mtm"], monthly["avg_pct_change_harga_pangan"])
    overall_rows.append(
        {
            "pasangan": "rata-rata nasional per bulan (inflasi_mtm vs harga pangan)",
            "unit": "bulan",
            **ts,
        }
    )
    return {
        "overall": pd.DataFrame(overall_rows),
        "by_month": pd.DataFrame(by_month),
        "monthly": monthly,
    }


def main() -> int:
    conn = get_postgres_connection()
    try:
        df = load_mart(conn)
    finally:
        conn.close()
    if df.empty:
        print("mart_inflasi_vs_harga is empty; run F3b (bps) and dbt build first.")
        return 1
    res = analyze(df)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    res["overall"].to_csv(EXPORT_DIR / "inflation_food_overall.csv", index=False, encoding="utf-8")
    res["by_month"].to_csv(
        EXPORT_DIR / "inflation_food_by_month.csv", index=False, encoding="utf-8"
    )
    res["monthly"].to_csv(EXPORT_DIR / "inflation_food_monthly.csv", index=False, encoding="utf-8")

    n_city_months = len(df)
    print(
        f"mart_inflasi_vs_harga: {n_city_months} city x month rows, {df['kode_vervar'].nunique()} cities, {df['bulan'].min()}..{df['bulan'].max()}"
    )
    print(f"rows with pct_change_harga_pangan: {int(df['pct_change_harga_pangan'].notna().sum())}")
    print("\n=== SPEARMAN CORRELATION (city inflation vs. food price change) ===")
    print(res["overall"].to_string(index=False))
    print("\n=== PER MONTH (province cross-section) ===")
    print(res["by_month"].to_string(index=False))
    print(
        "\nWARNING: correlation, NOT causation. Food prices are only 8 HDX WFP commodities (34 provinces; "
        "Jan-Feb 2026 has only 8 provinces); the IHK covers the whole consumption basket."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
