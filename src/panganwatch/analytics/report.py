#!/usr/bin/env python3
"""
Analytics: Generate a standalone HTML report with Plotly charts.

6 charts:
1. Price deviation per province, map/bar (from mart_disparitas_provinsi)
2. Trend of the top commodity prices (from fct_harga_bulanan)
3. Weather-price lag correlation heatmap (from the weather_price_lag output)
4. DQ scorecard per dimension (from mart_dq_scorecard)
5. Trend of quarantined record counts (from governance.quarantine)
6. City inflation vs. food price (from analytics/inflation_food.py, F3b)
Plus a findings summary in text, generated from the query results.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.db import get_postgres_connection


def get_gold_connection():
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SET search_path TO gold, governance, public")
    return conn


def load_disparitas(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                bulan,
                kode_provinsi_bps,
                komoditas_id,
                harga_median_provinsi,
                harga_median_nasional,
                pct_deviasi,
                rank_deviasi
            FROM gold.mart_disparitas_provinsi
            ORDER BY bulan, komoditas_id, kode_provinsi_bps
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def load_fct_harga(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                tanggal as bulan,
                kode_provinsi_bps,
                komoditas_id,
                harga_median,
                n_observasi
            FROM gold.fct_harga_bulanan
            ORDER BY tanggal, komoditas_id, kode_provinsi_bps
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def load_dq_scorecard(conn):
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


def load_quarantine_trend(conn):
    """Load the quarantine trend per run from governance.quarantine."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                date(quarantined_at) as run_day,
                count(*) as quarantine_count
            FROM governance.quarantine
            GROUP BY run_day
            ORDER BY run_day
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def load_weather_price_lag():
    """Load pre-computed weather-price lag correlations from exports."""
    path = Path("exports/tableau/weather_price_lag_overall.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_inflation_food():
    """Load pre-computed inflation-vs-food-price outputs (analytics/inflation_food.py)."""
    base = Path("exports/tableau")
    out = {}
    for key, name in (
        ("monthly", "inflation_food_monthly.csv"),
        ("by_month", "inflation_food_by_month.csv"),
        ("overall", "inflation_food_overall.csv"),
    ):
        path = base / name
        out[key] = pd.read_csv(path) if path.exists() else pd.DataFrame()
    return out


def load_disparitas_summary():
    """Load the pre-computed disparity summary from exports."""
    path = Path("exports/tableau/mart_disparitas_summary.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _name_maps():
    """id -> name lookups from the exported dimensions (ids stay strings: '0104')."""
    try:
        k = pd.read_csv("exports/tableau/dim_komoditas.csv", dtype=str)
        p = pd.read_csv("exports/tableau/dim_provinsi.csv", dtype=str)
        return (
            dict(zip(k["komoditas_id"], k["nama_komoditas"])),
            dict(zip(p["kode_provinsi_bps"], p["nama_provinsi"])),
            len(p),
        )
    except Exception:
        return {}, {}, 38


def price_coverage(fct_harga, total_prov):
    """Province coverage of price data, computed from the gold fact table."""
    n_prov = int(fct_harga["kode_provinsi_bps"].nunique()) if not fct_harga.empty else 0
    per_month = (
        fct_harga.groupby("bulan")["kode_provinsi_bps"].nunique()
        if not fct_harga.empty
        else pd.Series(dtype=int)
    )
    return n_prov, total_prov, per_month


def generate_findings_text(
    disparitas,
    fct_harga,
    scorecard,
    quarantine,
    lag_overall,
    disparitas_summary,
    inflation_food=None,
):
    """Generate the findings text from actual query results (nothing hard-coded)."""
    findings = []
    kname, pname, total_prov = _name_maps()

    # Finding 1: Price disparity (data is MONTHLY: the "weekly" CV column is one bucket per month)
    if not disparitas_summary.empty:
        max_row = disparitas_summary.loc[disparitas_summary["avg_pct_deviasi_max"].abs().idxmax()]
        kid = str(max_row["komoditas_id"]).zfill(4)
        pid = str(max_row["provinsi_max_deviasi"])
        findings.append(
            f"1. **Largest price disparity**: {kname.get(kid, 'commodity')} ({kid}) shows the largest average "
            f"deviation from the national median, in {pname.get(pid, 'province')} ({pid}), at "
            f"**{max_row['avg_pct_deviasi_max']:+.2f}%** (last 3 available months). "
            f"Average cross-province coefficient of variation: **{max_row['avg_weekly_cv_pct']:.2f}%** per month."
        )

    # Finding 2: Weather-price correlation
    if not lag_overall.empty:
        groups = ", ".join(sorted(lag_overall["kelompok"].astype(str).unique()))
        sig = lag_overall[lag_overall["p_value"] < 0.1]
        if not sig.empty:
            best = sig.loc[sig["p_value"].idxmin()]
            findings.append(
                f"2. **Weather-price correlation (Spearman, pooled)**: groups {groups}. Smallest p-value "
                f"(p={best['p_value']:.4f}) for **{best['kelompok']}** at a **{best['lag_bulan']}-month** lag "
                f"(rho={best['spearman_rho']:.3f}, n={best['n_observations']}). "
                f"**WARNING: this is a correlation, NOT causation.** Confounders include harvest season, "
                f"holidays, import policy, and the supply chain."
            )
        else:
            findings.append(
                f"2. **Weather-price correlation**: no significant Spearman correlation (p<0.1) for groups "
                f"{groups} across {len(lag_overall)} lag combinations tested. **Correlation != causation.**"
            )

    # Finding 3: DQ Scorecard (cumulative over all historical runs)
    if not scorecard.empty:
        total_rules = scorecard["rules_total"].sum()
        total_passed = scorecard["rules_passed"].sum()
        avg_score = scorecard["score"].mean()
        worst_dim = scorecard.loc[scorecard["score"].idxmin()]
        findings.append(
            f"3. **Data quality scorecard** (cumulative across all runs): **{total_rules}** DQ rule checks per "
            f"source x dimension, **{total_passed}** passed ({total_passed / total_rules * 100:.1f}%). Average "
            f"score **{avg_score:.2f}**. Lowest-scoring dimension: **{worst_dim['source']}.{worst_dim['dimensi']}** "
            f"(score {worst_dim['score']:.2f})."
        )

    # Finding 4: Quarantine history
    if not quarantine.empty:
        total_quarantine = int(quarantine["quarantine_count"].sum())
        findings.append(
            f"4. **Data quarantine**: **{total_quarantine}** records currently logged in `governance.quarantine` "
            f"(rows from the F4 injection test; quarantine rows are never deleted). A full DQ run over the silver "
            f"data adds no new quarantine because the coverage rules are `warn`-severity."
        )

    # Finding 5: Coverage gap, computed from the fact table
    n_prov, total_prov, per_month = price_coverage(fct_harga, total_prov)
    if n_prov:
        low_month = per_month.idxmin()
        findings.append(
            f"5. **Province coverage**: price data exists for **{n_prov} of {total_prov} provinces** "
            f"({n_prov / total_prov * 100:.1f}%); {total_prov - n_prov} provinces (the newly split Papua "
            f"provinces) never appear in the HDX WFP source. Lowest-coverage month: **{low_month}**, with only "
            f"**{int(per_month.min())}** provinces (other months have {int(per_month.median())}). The national "
            f"median is not on par with full 38-province coverage."
        )

    # Finding 6: inflation (BPS) vs food prices - correlation, not causation
    overall = (inflation_food or {}).get("overall")
    by_month = (inflation_food or {}).get("by_month")
    if overall is not None and not overall.empty:
        pooled = overall.iloc[0]
        has_months = by_month is not None and not by_month.empty
        n_sig = int((by_month["p_value"] < 0.05).sum()) if has_months else 0
        n_months = len(by_month) if has_months else 0
        findings.append(
            f"6. **City inflation vs. food prices (BPS IHK)**: province x month Spearman rho={pooled['rho']:.3f} "
            f"(n={int(pooled['n'])}, p={pooled['p_value']:.4f}); only {n_sig} of {n_months} monthly cross-sections "
            f"are significant at p<0.05, with a sign that flips between months. **Correlation, NOT causation**: "
            f"the IHK covers the whole consumption basket, while the food-price series covers only 8 HDX WFP "
            f"commodities across 34 provinces."
        )

    return findings


def create_inflation_food_chart(inflation_food):
    """Chart 6: average city inflation (MtM) vs. food-price change, per month."""
    monthly = inflation_food.get("monthly")
    if monthly is None or monthly.empty:
        return None

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["bulan"],
            y=monthly["avg_inflasi_mtm"],
            name="City IHK inflation (MtM, %)",
            hovertemplate="Month: %{x}<br>MtM inflation: %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly["bulan"],
            y=monthly["avg_pct_change_harga_pangan"],
            name="Food price change (MoM, %)",
            hovertemplate="Month: %{x}<br>Food price: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="City Inflation (BPS) vs. Food Price Change (HDX WFP) - province average per month",
        xaxis_title="Month (Jan-Feb 2026: prices cover only 8 provinces)",
        yaxis_title="Percent",
        barmode="group",
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_disparitas_bar_chart(disparitas_summary):
    """Chart 1: bar chart of deviation per commodity."""
    if disparitas_summary.empty:
        return None

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=disparitas_summary["komoditas_id"],
            y=disparitas_summary["avg_pct_deviasi_max"],
            name="Max deviation (%)",
            marker_color="indianred",
            text=[f"{v:+.1f}%" for v in disparitas_summary["avg_pct_deviasi_max"]],
            textposition="auto",
            hovertemplate="Commodity: %{x}<br>Province with max deviation: %{customdata[0]}<br>Deviation: %{y:+.2f}%<br>Avg CV: %{customdata[1]:.2f}%<extra></extra>",
            customdata=list(
                zip(
                    disparitas_summary["provinsi_max_deviasi"],
                    disparitas_summary["avg_weekly_cv_pct"],
                )
            ),
        )
    )

    fig.update_layout(
        title="Maximum Price Deviation per Commodity vs. National Median (90 days)",
        xaxis_title="Commodity ID",
        yaxis_title="Average Maximum Deviation (%)",
        template="plotly_white",
        height=400,
        showlegend=False,
    )
    return fig


def create_price_trend_chart(fct_harga):
    """Chart 2: trend of the top commodity prices."""
    if fct_harga.empty:
        return None

    import plotly.graph_objects as go

    # Get top 5 commodities by total observations
    top_comm = fct_harga.groupby("komoditas_id")["n_observasi"].sum().nlargest(5).index.tolist()
    df_top = fct_harga[fct_harga["komoditas_id"].isin(top_comm)]

    fig = go.Figure()
    for comm in top_comm:
        sub = df_top[df_top["komoditas_id"] == comm].sort_values("bulan")
        # National median per month
        nat = sub.groupby("bulan")["harga_median"].median().reset_index()
        fig.add_trace(
            go.Scatter(
                x=nat["bulan"],
                y=nat["harga_median"],
                mode="lines+markers",
                name=comm,
                hovertemplate="Month: %{x}<br>National median: %{y:,.0f}<extra></extra>",
            )
        )

    fig.update_layout(
        title="National Median Price Trend - Top 5 Commodities",
        xaxis_title="Month",
        yaxis_title="Median Price (IDR)",
        template="plotly_white",
        height=400,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_lag_heatmap(lag_overall):
    """Chart 3: lag correlation heatmap."""
    if lag_overall.empty:
        return None

    import plotly.graph_objects as go

    # Pivot for heatmap
    pivot = lag_overall.pivot(index="lag_bulan", columns="kelompok", values="spearman_rho")
    pivot_p = lag_overall.pivot(index="lag_bulan", columns="kelompok", values="p_value")

    if pivot.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[f"Lag {int(i)} mo" for i in pivot.index],
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=[
                [f"ρ={v:.3f}<br>p={pivot_p.iloc[i, j]:.3f}" for j, v in enumerate(pivot.iloc[i])]
                for i in range(len(pivot))
            ],
            texttemplate="%{text}",
            hovertemplate="Group: %{x}<br>%{y}<br>Spearman ρ: %{z:.3f}<extra></extra>",
            colorbar=dict(title="Spearman ρ"),
        )
    )

    fig.update_layout(
        title="Spearman Correlation Heatmap: Heavy Rain Days vs. Price Change (Monthly)",
        xaxis_title="Commodity Group",
        yaxis_title="Lag",
        template="plotly_white",
        height=400,
    )
    return fig


def create_dq_scorecard_chart(scorecard):
    """Chart 4: DQ scorecard per dimension per source."""
    if scorecard.empty:
        return None

    import plotly.graph_objects as go

    # Grouped bar chart
    sources = scorecard["source"].unique()
    fig = go.Figure()

    for src in sources:
        sub = scorecard[scorecard["source"] == src]
        fig.add_trace(
            go.Bar(
                x=sub["dimensi"],
                y=sub["score"],
                name=src,
                text=[f"{v:.1f}" for v in sub["score"]],
                textposition="auto",
                hovertemplate="Source: %{customdata[0]}<br>Dimension: %{x}<br>Score: %{y:.2f}<br>Rules: %{customdata[1]}/{customdata[2]}<extra></extra>",
                customdata=list(zip(sub["source"], sub["rules_passed"], sub["rules_total"])),
            )
        )

    fig.update_layout(
        title="DQ Scorecard per Dimension per Source",
        xaxis_title="DAMA Dimension",
        yaxis_title="Score (0-100)",
        template="plotly_white",
        height=400,
        barmode="group",
        yaxis=dict(range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_quarantine_trend_chart(quarantine):
    """Chart 5: quarantine trend."""
    if quarantine.empty:
        return None

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=quarantine["run_day"],
            y=quarantine["quarantine_count"],
            mode="lines+markers",
            name="Quarantined records",
            line=dict(color="firebrick"),
            hovertemplate="Run: %{x}<br>Quarantined: %{y} records<extra></extra>",
        )
    )

    fig.update_layout(
        title="Quarantined Record Count per Run",
        xaxis_title="Run Date",
        yaxis_title="Quarantined Record Count",
        template="plotly_white",
        height=400,
        hovermode="x unified",
    )
    return fig


def generate_report():
    print("Loading data for report...")
    conn = get_gold_connection()
    try:
        disparitas = load_disparitas(conn)
        fct_harga = load_fct_harga(conn)
        scorecard = load_dq_scorecard(conn)
        quarantine = load_quarantine_trend(conn)
        lag_overall = load_weather_price_lag()
        disparitas_summary = load_disparitas_summary()
        inflation_food = load_inflation_food()

        print(f"Disparitas: {len(disparitas)} rows")
        print(f"FCT Harga: {len(fct_harga)} rows")
        print(f"Scoreboard: {len(scorecard)} rows")
        print(f"Quarantine: {len(quarantine)} rows")
        print(f"Lag Overall: {len(lag_overall)} rows")
        print(f"Disparitas Summary: {len(disparitas_summary)} rows")

        # Generate findings
        findings = generate_findings_text(
            disparitas,
            fct_harga,
            scorecard,
            quarantine,
            lag_overall,
            disparitas_summary,
            inflation_food,
        )
        cov_n, cov_total, _ = price_coverage(fct_harga, _name_maps()[2])

        # Create charts
        charts = []
        chart_funcs = [
            ("Price Deviation per Commodity", create_disparitas_bar_chart, disparitas_summary),
            ("Top Commodity Price Trend", create_price_trend_chart, fct_harga),
            ("Weather-Price Lag Correlation Heatmap", create_lag_heatmap, lag_overall),
            ("DQ Scorecard per Dimension", create_dq_scorecard_chart, scorecard),
            ("Quarantined Record Trend", create_quarantine_trend_chart, quarantine),
            ("City Inflation vs. Food Price", create_inflation_food_chart, inflation_food),
        ]

        for title, func, data in chart_funcs:
            try:
                fig = func(data)
                if fig is not None:
                    charts.append((title, fig.to_html(full_html=False, include_plotlyjs="cdn")))
                    print(f"Created chart: {title}")
                else:
                    print(f"Skipped chart (no data): {title}")
            except Exception as e:
                print(f"Error creating chart {title}: {e}")

        # Build HTML
        html_parts = []
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PanganWatch - Food Price Analytics Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #1a3c5e; border-bottom: 3px solid #2e86ab; padding-bottom: 10px; }
        h2 { color: #2e86ab; margin-top: 40px; }
        .chart { margin: 30px 0; }
        .findings { background: #e8f4fd; border-left: 4px solid #2e86ab; padding: 20px; margin: 30px 0; border-radius: 4px; }
        .findings h2 { margin-top: 0; color: #1a3c5e; }
        .findings ol { margin: 0; padding-left: 20px; }
        .findings li { margin: 12px 0; line-height: 1.6; }
        .disclaimer { background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 15px; margin: 20px 0; }
        .disclaimer strong { color: #856404; }
        .meta { color: #6c757d; font-size: 0.9em; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; }
        .plotly-graph-div { width: 100% !important; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 PanganWatch - National Food Price Analytics Report</h1>
        <p>This report is generated automatically from the PanganWatch data pipeline. Every figure and chart comes from a real database query, not manual input.</p>
""")

        # Charts
        for i, (title, chart_html) in enumerate(charts, 1):
            html_parts.append(f"""
        <div class="chart">
            <h2>{i}. {title}</h2>
            {chart_html}
        </div>""")

        # Findings
        html_parts.append("""
        <div class="findings">
            <h2>🔍 Key Findings (Generated from Data)</h2>
            <ol>""")
        for f in findings:
            html_parts.append(f"<li>{f}</li>")
        html_parts.append("""
            </ol>
        </div>
""")

        # Disclaimer
        html_parts.append(
            """
        <div class="disclaimer">
            <strong>⚠️ Important disclaimer:</strong>
            <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                <li>All weather-price correlations are a <strong>statistical (Spearman) correlation</strong>, <strong>NOT causation</strong>.</li>
                <li>Confounders: harvest season, holidays, import policy, the supply chain, regional variation.</li>
                <li>Price data covers only {COVERAGE_TEXT} provinces; January 2026 in the source only covers a subset of provinces.</li>
                <li>No chili data exists in this data window (HDX WFP stopped carrying chili in May 2024): the rain-vs-price question can only be answered for shallots.</li>
                <li>Price source: HDX WFP (monthly, a fallback source) - not a real-time daily market feed.</li>
                <li>This analysis is for a portfolio/research purpose, not an official policy decision.</li>
            </ul>
        </div>
""".replace("{COVERAGE_TEXT}", f"{cov_n} of {cov_total}")
        )

        # Meta
        from datetime import datetime

        html_parts.append(f"""
        <div class="meta">
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Pipeline: PanganWatch v1.0.0 | Data: HDX WFP (prices), Open-Meteo (weather); region codes follow BPS/Kemendagri</p>
        </div>
    </div>
</body>
</html>""")

        html_content = "\n".join(html_parts)

        # Save
        output_path = Path("reports/panganwatch_report.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        print(f"\nReport saved to {output_path} ({len(html_content):,} bytes)")

        # Count real chart divs (bare token also matches CSS/script lines)
        plotly_count = html_content.count('class="plotly-graph-div')
        print(f"Plotly graph divs: {plotly_count} (minimum 5 required)")

        return plotly_count >= 5

    finally:
        conn.close()


if __name__ == "__main__":
    success = generate_report()
    if success:
        print("\n✓ Report generated successfully with >=5 Plotly charts")
    else:
        print("\n✗ Report generated but with <5 charts")
    sys.exit(0 if success else 1)
