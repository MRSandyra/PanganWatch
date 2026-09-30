#!/usr/bin/env python3
"""
Analytics: DQ Trust Scorecard - a quality-score summary per source per dimension, and the trend per run.

Reads data from gold.mart_dq_scorecard and governance.dq_results.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection


def get_gold_connection():
    """Get connection and set search_path to gold, governance schemas."""
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SET search_path TO gold, governance, public")
    return conn


def load_mart_dq_scorecard(conn):
    """Load mart_dq_scorecard from gold schema."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                source,
                dimensi,
                rules_total,
                rules_passed,
                rows_checked,
                rows_failed,
                score
            FROM gold.mart_dq_scorecard
            ORDER BY source, dimensi
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def load_dq_results_trend(conn):
    """Load DQ results trend per run from governance.dq_results."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                run_id,
                dataset,
                rule_id,
                dimension,
                severity,
                rows_checked,
                rows_failed,
                pass_rate,
                checked_at
            FROM governance.dq_results
            WHERE rows_checked > 0
            ORDER BY checked_at, dataset, rule_id
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def compute_source_dim_summary(scorecard):
    """Summary per source per dimension."""
    if scorecard.empty:
        return pd.DataFrame()

    summary = (
        scorecard.groupby(["source", "dimensi"])
        .agg(
            rules_total=("rules_total", "sum"),
            rules_passed=("rules_passed", "sum"),
            rules_failed=(
                "rules_total",
                lambda x: x.sum() - scorecard.loc[x.index, "rules_passed"].sum(),
            ),
            total_rows_checked=("rows_checked", "sum"),
            total_rows_failed=("rows_failed", "sum"),
            avg_score=("score", "mean"),
        )
        .reset_index()
    )

    summary["pass_rate_pct"] = round((summary["rules_passed"] / summary["rules_total"] * 100), 2)
    summary["row_fail_rate_pct"] = round(
        (summary["total_rows_failed"] / summary["total_rows_checked"] * 100), 2
    )

    return summary


def compute_run_trend(dq_results):
    """Compute trend per run."""
    if dq_results.empty:
        return pd.DataFrame()

    trend = (
        dq_results.groupby("run_id")
        .agg(
            n_rules=("rule_id", "nunique"),
            n_datasets=("dataset", "nunique"),
            total_rows_checked=("rows_checked", "sum"),
            total_rows_failed=("rows_failed", "sum"),
            avg_pass_rate=("pass_rate", "mean"),
            run_date=("checked_at", "min"),
        )
        .reset_index()
    )

    trend["overall_pass_rate_pct"] = round(trend["avg_pass_rate"], 2)
    trend["row_fail_rate_pct"] = round(
        (trend["total_rows_failed"] / trend["total_rows_checked"] * 100), 2
    )
    trend = trend.sort_values("run_date")

    return trend


def compute_dimension_trend(dq_results):
    """Compute trend per dimension per run."""
    if dq_results.empty:
        return pd.DataFrame()

    trend = (
        dq_results.groupby(["run_id", "dimension"])
        .agg(
            n_rules=("rule_id", "nunique"),
            total_rows_checked=("rows_checked", "sum"),
            total_rows_failed=("rows_failed", "sum"),
            avg_pass_rate=("pass_rate", "mean"),
            run_date=("checked_at", "min"),
        )
        .reset_index()
    )

    trend["dim_pass_rate_pct"] = round(trend["avg_pass_rate"], 2)
    trend["dim_row_fail_rate_pct"] = round(
        (trend["total_rows_failed"] / trend["total_rows_checked"] * 100), 2
    )
    trend = trend.sort_values(["run_date", "dimension"])

    return trend


def main():
    print("Loading DQ scorecard and results...")
    conn = get_gold_connection()
    try:
        scorecard = load_mart_dq_scorecard(conn)
        dq_results = load_dq_results_trend(conn)

        print(f"Loaded mart_dq_scorecard: {len(scorecard)} rows")
        print(f"Loaded governance.dq_results: {len(dq_results)} rows")

        if scorecard.empty and dq_results.empty:
            print("No data found. Skipping.")
            return

        # Source-dimension summary
        print("\n=== SOURCE x DIMENSION SUMMARY (from mart_dq_scorecard) ===")
        source_dim = compute_source_dim_summary(scorecard)
        if not source_dim.empty:
            print(source_dim.to_string(index=False))
        else:
            print("No scorecard data.")

        # Run trend
        print("\n=== RUN TREND (from governance.dq_results) ===")
        run_trend = compute_run_trend(dq_results)
        if not run_trend.empty:
            print(run_trend.to_string(index=False))
        else:
            print("No DQ results trend data.")

        # Dimension trend per run
        print("\n=== DIMENSION TREND PER RUN ===")
        dim_trend = compute_dimension_trend(dq_results)
        if not dim_trend.empty:
            print(dim_trend.to_string(index=False))
        else:
            print("No dimension trend data.")

        # Save to exports for Tableau
        export_dir = Path("exports/tableau")
        export_dir.mkdir(parents=True, exist_ok=True)

        if not source_dim.empty:
            path = export_dir / "dq_trust_source_dimension.csv"
            source_dim.to_csv(path, index=False, encoding="utf-8")
            print(f"\nSaved source-dimension summary to {path}")

        if not run_trend.empty:
            path = export_dir / "dq_trust_run_trend.csv"
            run_trend.to_csv(path, index=False, encoding="utf-8")
            print(f"Saved run trend to {path}")

        if not dim_trend.empty:
            path = export_dir / "dq_trust_dimension_trend.csv"
            dim_trend.to_csv(path, index=False, encoding="utf-8")
            print(f"Saved dimension trend to {path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
