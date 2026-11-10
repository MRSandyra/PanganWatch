# Baseline audit

**Status:** COMPLETE (repository inspection, 2026-11-09). This is an evidence-based mapping of the checked-in local platform, not a cloud execution report.

| Local component | Evidence | Migration target |
|---|---|---|
| HDX/WFP raw prices in MongoDB with SHA-256 envelope | `src/panganwatch/sources/hdx_wfp.py`, `src/panganwatch/bronze.py` | immutable file + UC Volume + Bronze Delta |
| Open-Meteo archive daily weather | `src/panganwatch/sources/open_meteo.py` | immutable JSON + Bronze Delta |
| BPS city IHK, API-key gated | `src/panganwatch/sources/bps.py` | allowed snapshot only after BPS terms review |
| Price / weather / inflation Silver upserts | `src/panganwatch/silver/*.py`, `sql/ddl/init_governance.sql` | explicit Spark schemas and Delta MERGE |
| 27 DAMA DQ rules, post-load gate | `config/dq_rules.yml`, `src/panganwatch/dq/engine.py` | `pw_governance.dq_results` / `quarantine`; warnings remain visible |
| dbt Gold marts | `dbt/panganwatch/models/marts/` | Spark/Databricks SQL Gold marts |
| Airflow daily/monthly DAGs | `dags/panganwatch_daily.py`, `dags/panganwatch_monthly_bps.py` | one manual Lakeflow batch job |
| Kafka current-weather stream | `src/panganwatch/stream/`, `docs/streaming.md` | retained locally; out of cloud batch MVP |

## Business semantics and known limits

The retained baseline answers regional price disparity, weather-price association (not causation), source quality, and inflation comparison. `README.md` documents a historical run with 20,864 price rows, at least 17,708 daily weather rows, 34/38 price provinces, 8/14 commodities, and January 2026 partial coverage. Those are published historical values, not migration pass criteria until the original frozen input and filters are recovered.

The WFP source lacks Papua Selatan, Papua Tengah, Papua Pegunungan, and Papua Barat Daya; chili is absent in the documented window. Existing DQ warnings `HP-012` and `HP-014` must remain warnings, never imputed away. `CH-007` is a documented historical engine incident, not evidence of incorrect weather data. See `docs/governance/incident_log.md`.

## Git safety

At audit: branch `main`, clean worktree, HEAD `2fc4529 Initial Commit`. The dedicated branch `feature/databricks-free-edition` was then created successfully; no user work was discarded.
