#!/usr/bin/env python3
"""
Analytics: weather (heavy rain) vs. price-change correlation, with a monthly lag.

For the chili and shallot groups:
- Spearman correlation between the number of heavy-rain days per month per
  province and the percentage price change, at lags of 0, 1, 2, 3, 4 months
- Report the coefficient, p-value, and observation count
- Explicit warning: CORRELATION != CAUSATION
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection


def get_gold_connection():
    """Get connection and set search_path to gold schema."""
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SET search_path TO gold, public")
    return conn


def load_mart_cuaca_harga(conn):
    """Load mart_cuaca_harga_bulanan from gold schema."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                bulan,
                kode_provinsi_bps,
                kelompok,
                hari_hujan_lebat,
                total_hujan_mm,
                harga_median,
                pct_change_mom
            FROM gold.mart_cuaca_harga_bulanan
            ORDER BY bulan, kode_provinsi_bps, kelompok
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def compute_lag_correlations(df, max_lag=4):
    """Compute Spearman correlation between hari_hujan_lebat and price change at different lags."""
    results = []

    # Only analyze cabai and bawang groups
    target_groups = ["cabai", "bawang"]
    df = df[df["kelompok"].isin(target_groups)].copy()

    # Convert Decimal to float
    df["pct_change_mom"] = pd.to_numeric(df["pct_change_mom"], errors="coerce")
    df["hari_hujan_lebat"] = pd.to_numeric(df["hari_hujan_lebat"], errors="coerce")
    df["harga_median"] = pd.to_numeric(df["harga_median"], errors="coerce")
    df["total_hujan_mm"] = pd.to_numeric(df["total_hujan_mm"], errors="coerce")

    if df.empty:
        return pd.DataFrame()

    # For each province and commodity group, compute correlations
    for (prov, group), sub_df in df.groupby(["kode_provinsi_bps", "kelompok"]):
        sub_df = sub_df.sort_values("bulan").reset_index(drop=True)

        if len(sub_df) < max_lag + 3:  # Need enough data points
            continue

        for lag in range(max_lag + 1):
            # hari_hujan_lebat at month t vs pct_change_mom at month t+lag
            if lag == 0:
                x = sub_df["hari_hujan_lebat"]
                y = sub_df["pct_change_mom"]
            else:
                x = sub_df["hari_hujan_lebat"].iloc[:-lag]
                y = sub_df["pct_change_mom"].iloc[lag:]

            # Remove NaN pairs
            mask = x.notna() & y.notna()
            if mask.sum() < 5:  # Minimum observations
                continue

            x_clean = x[mask]
            y_clean = y[mask]

            # Spearman correlation
            try:
                rho, p_value = stats.spearmanr(x_clean, y_clean)
                if np.isnan(rho):
                    rho, p_value = 0.0, 1.0
            except Exception:
                rho, p_value = 0.0, 1.0

            results.append(
                {
                    "kode_provinsi_bps": prov,
                    "kelompok": group,
                    "lag_bulan": lag,
                    "spearman_rho": round(rho, 4),
                    "p_value": round(p_value, 6),
                    "n_observations": int(mask.sum()),
                    "x_mean": round(x_clean.mean(), 2),
                    "y_mean": round(y_clean.mean(), 4),
                    "x_std": round(x_clean.std(), 2),
                    "y_std": round(y_clean.std(), 4),
                }
            )

    return pd.DataFrame(results)


def compute_overall_correlations(df, max_lag=4):
    """Compute overall correlations pooling all provinces."""
    results = []
    target_groups = ["cabai", "bawang"]
    df = df[df["kelompok"].isin(target_groups)].copy()

    # Convert Decimal to float
    df["pct_change_mom"] = pd.to_numeric(df["pct_change_mom"], errors="coerce")
    df["hari_hujan_lebat"] = pd.to_numeric(df["hari_hujan_lebat"], errors="coerce")
    df["harga_median"] = pd.to_numeric(df["harga_median"], errors="coerce")
    df["total_hujan_mm"] = pd.to_numeric(df["total_hujan_mm"], errors="coerce")

    if df.empty:
        return pd.DataFrame()

    for group in target_groups:
        sub_df = df[df["kelompok"] == group]

        for lag in range(max_lag + 1):
            # Align by province and month
            aligned = []
            for prov, prov_df in sub_df.groupby("kode_provinsi_bps"):
                prov_df = prov_df.sort_values("bulan").reset_index(drop=True)
                if len(prov_df) > lag:
                    x_vals = prov_df["hari_hujan_lebat"].iloc[:-lag].values
                    y_vals = prov_df["pct_change_mom"].iloc[lag:].values
                    for xv, yv in zip(x_vals, y_vals):
                        if pd.notna(xv) and pd.notna(yv):
                            aligned.append((xv, yv))

            if len(aligned) < 5:
                continue
            x = pd.Series([a[0] for a in aligned])
            y = pd.Series([a[1] for a in aligned])

            mask = x.notna() & y.notna()
            if mask.sum() < 5:
                continue

            x_clean = x[mask]
            y_clean = y[mask]
            # Spearman correlation
            try:
                rho, p_value = stats.spearmanr(x_clean, y_clean)
                if np.isnan(rho):
                    rho, p_value = 0.0, 1.0
            except Exception:
                rho, p_value = 0.0, 1.0

            results.append(
                {
                    "kelompok": group,
                    "lag_bulan": lag,
                    "spearman_rho": round(rho, 4),
                    "p_value": round(p_value, 6),
                    "n_observations": int(mask.sum()),
                    "x_mean": round(x_clean.mean(), 2),
                    "y_mean": round(y_clean.mean(), 4),
                    "x_std": round(x_clean.std(), 2),
                    "y_std": round(y_clean.std(), 4),
                }
            )

    return pd.DataFrame(results)


def main():
    print("Loading mart_cuaca_harga_bulanan from gold schema...")
    conn = get_gold_connection()
    try:
        df = load_mart_cuaca_harga(conn)
        print(f"Loaded {len(df)} rows from mart_cuaca_harga_bulanan")

        if df.empty:
            print("No data found. Skipping.")
            return

        print(f"Groups: {df['kelompok'].unique()}")
        print(f"Provinces: {df['kode_provinsi_bps'].nunique()}")
        print(f"Month range: {df['bulan'].min()} to {df['bulan'].max()}")

        # Per-province correlations
        print("\n=== PER-PROVINCE CORRELATIONS (Spearman, monthly) ===")
        per_prov = compute_lag_correlations(df, max_lag=4)
        if not per_prov.empty:
            # Show significant ones (p < 0.1)
            sig = per_prov[per_prov["p_value"] < 0.1].sort_values("p_value")
            print(f"Significant (p<0.1): {len(sig)} out of {len(per_prov)}")
            if len(sig) > 0:
                print(sig.to_string(index=False))
            else:
                print("No significant correlations at p<0.1")
                print(per_prov.head(20).to_string(index=False))
        else:
            print("No correlations computed.")

        # Overall correlations
        print("\n=== OVERALL CORRELATIONS (pooled across provinces) ===")
        overall = compute_overall_correlations(df, max_lag=4)
        if not overall.empty:
            print(overall.to_string(index=False))
        else:
            print("No overall correlations computed.")

        # Save to exports for Tableau
        export_dir = Path("exports/tableau")
        export_dir.mkdir(parents=True, exist_ok=True)

        if not per_prov.empty:
            per_prov_path = export_dir / "weather_price_lag_per_province.csv"
            per_prov.to_csv(per_prov_path, index=False, encoding="utf-8")
            print(f"\nSaved per-province correlations to {per_prov_path}")

        if not overall.empty:
            overall_path = export_dir / "weather_price_lag_overall.csv"
            overall.to_csv(overall_path, index=False, encoding="utf-8")
            print(f"Saved overall correlations to {overall_path}")

        # Print disclaimer
        print("\n" + "=" * 70)
        print("WARNING: CORRELATION != CAUSATION")
        print("=" * 70)
        print("The results above show a statistical (Spearman) correlation between")
        print("the number of heavy-rain days per month and the percentage price")
        print("change at various lags (0-4 months).")
        print("")
        print("This does NOT prove a cause-and-effect relationship. Confounders")
        print("that may affect both variables include:")
        print("  - Harvest season (lowers prices, correlated with rainfall)")
        print("  - Holidays / national holidays (affect demand and distribution)")
        print("  - Government policy (imports, government stockpiles, price ceilings)")
        print("  - Supply chain & logistics (storms disrupt distribution)")
        print(
            "  - Commodity specifics (different chili/shallot varieties respond to rain differently)"
        )
        print("  - Regional variation (irrigation, elevation, soil type)")
        print("")
        print("Interpret with caution, and confirm with a more rigorous causal")
        print("analysis (e.g. diff-in-diff, instrumental variables, an RCT).")
        print("=" * 70)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
