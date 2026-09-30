# Architecture

## Overview

PanganWatch follows a **medallion architecture** with fit-for-purpose storage:

- **Bronze** (MongoDB): Raw API payloads with `_meta` envelope (source, endpoint, hash SHA-256, run_id, fetched_at, TTL 90d).
- **Silver** (PostgreSQL): Cleaned, validated, upsert-idempotent relational tables with FK constraints.
- **Gold** (PostgreSQL, dbt): Dimensional model + analytical marts ready for BI.
- **Governance** (PostgreSQL): `pipeline_runs`, `dq_results`, `quarantine` — run-level audit trail.

---

## Batch Data Flow

```mermaid
flowchart TD
    subgraph Sources
        HDX[HDX WFP API<br/>monthly prices]
        OM_H[Open-Meteo Archive<br/>historical weather]
        BPS[BPS WebAPI<br/>IHK 150 kab/kota]
    end

    subgraph Bronze["Bronze (MongoDB, TTL 90d)"]
        B_HDX[hdx_wfp_prices]
        B_OM[open_meteo_daily]
        B_BPS[bps_inflation]
    end

    subgraph Ingestion["Ingestion (Python, idempotent)"]
        ENV[bronze.py store_raw<br/>envelope AD-02]
        MAP[wilayah/komoditas mapping<br/>via ref_alias seeds]
        SIL[silver loader<br/>upsert on natural key]
    end

    subgraph Silver["Silver (PostgreSQL)"]
        S_HP[harga_pangan]
        S_CH[cuaca_harian]
        S_IK[inflasi_kota]
    end

    subgraph DQG["DQ gate (Airflow task dq_check)"]
        DQ[DQ rule engine<br/>27 rules, 6 dimensions]
    end

    subgraph Governance["Governance layer"]
        PR[pipeline_runs]
        DQ_R[dq_results]
        QR[quarantine]
    end

    subgraph Transform["dbt transform"]
        DBT[dbt build<br/>8 gold models<br/>PASS=134]
    end

    subgraph Gold["Gold (PostgreSQL)"]
        DIM[dim_provinsi<br/>dim_komoditas<br/>dim_tanggal]
        FCT[fct_harga_bulanan]
        MART[mart_disparitas_provinsi<br/>mart_cuaca_harga_bulanan<br/>mart_dq_scorecard<br/>mart_inflasi_vs_harga]
    end

    HDX --> ENV
    OM_H --> ENV
    BPS --> B_BPS --> S_IK --> DQ
    S_IK --> DBT
    ENV --> MAP --> SIL
    SIL --> S_HP & S_CH
    SIL --> PR
    S_HP & S_CH --> DQ
    DQ -->|error rows| QR
    DQ -->|results| DQ_R
    DQ_R --> DBT
    S_HP & S_CH --> DBT --> DIM & FCT & MART
```

### Key batch properties
- **Idempotency**: unique index `(_meta.source, _meta.payload_sha256)` in MongoDB; upsert on natural key in Postgres.
- **DQ is a post-load gate, not inline**: `DQEngine.check_records()` runs in the Airflow task `dq_check` over the whole silver tables after ingestion (DEC-029); error-severity failures are written to `governance.quarantine` and results to `governance.dq_results`, but **rows are not removed from silver**. Only the injection test (`scripts/inject_bad_records.py`) exercises the "quarantine instead of load" path. `warn` rules (e.g. province coverage `HP-014`) never quarantine.
- **Grain**: HDX WFP is monthly (one snapshot per month-day-15); marts use monthly grain (DEC-010).

---

## Streaming Data Flow

```mermaid
flowchart LR
    subgraph Producer
        P[weather-producer<br/>poll every 900s<br/>38 provinces]
    end

    subgraph Kafka["Kafka (KRaft single-node)"]
        RAW[weather.current.raw<br/>3 partitions]
        DLQ[weather.current.dlq<br/>1 partition]
        ALERT[weather.alert<br/>1 partition]
    end

    subgraph Consumer
        C[weather-consumer<br/>group: panganwatch-weather-sink]
        VAL[Pydantic validation<br/>WeatherCurrentV1]
        UPSERT[upsert to<br/>silver.cuaca_terkini]
        BRONZE_RT[store raw to<br/>bronze open_meteo_current]
    end

    subgraph Postgres
        S3[silver.cuaca_terkini]
    end

    P -->|produce| RAW
    RAW --> C
    C --> VAL
    VAL -->|valid| UPSERT & BRONZE_RT
    VAL -->|invalid| DLQ
    UPSERT --> S3
    C -->|rain >=50mm| ALERT
```

### Key streaming properties
- **Data contract**: Pydantic v2 models, JSON Schema exported to `contracts/`.
- **DLQ**: invalid messages go to `weather.current.dlq` with headers (error_reason, original_topic, original_offset, failed_at); offset committed (at-least-once, idempotent upsert).
- **Alerts**: rain >=50mm (BMKG "lebat" threshold) → `weather.alert` topic + `governance.weather_alerts` table.
- **Reconnect**: consumer has `_reconnect_postgres()` for dropped connections (DEC-032).

---

## Orchestration (Airflow)

```mermaid
flowchart TD
    D1[panganwatch_daily<br/>10:00 WIB daily]
    D2[panganwatch_monthly_bps<br/>monthly - BPS inflation]
    D3[panganwatch_reference<br/>manual - dbt seed]
    D4[panganwatch_retention<br/>weekly - cleanup]

    D1 --> T1[ingest_harga] --> T2[ingest_cuaca_harian] --> T3[dq_check] --> T4[dbt_build] --> T5[export_bi SKIPPED] --> T6[build_report SKIPPED]
    D2 --> B1[ingest_bps] --> B2[dbt_build_bps]
    D3 --> R1[dbt_seed]
    D4 --> C1[delete resolved quarantine >180d] --> C2[verify MongoDB TTL]
```

### Airflow properties
- **4 DAGs**, all import without errors; `dags test panganwatch_daily` and `panganwatch_retention` both exit 0.
- **Failure callback**: writes `failed` status to `governance.pipeline_runs` via `dags/_common.py:write_failure_to_governance`.
- **dbt in separate venv**: `/home/airflow/dbt-venv` (DEC-030); `DBT_BIN` env var as single source of truth.
- **No secrets in DAG code**: all via `os.environ` / `panganwatch.config`.

---

## Governance Layer

| Artifact | Source | Description |
|----------|--------|-------------|
| `governance.pipeline_runs` | PostgreSQL | Run-level audit (source, started_at, status, rows) |
| `governance.dq_results` | PostgreSQL | Append-only history of per-rule results (pass_rate, rows_checked/failed); never deleted |
| `governance.quarantine` | PostgreSQL | Append-only; error-severity DQ failures with natural_key + record JSONB (currently only the 8 rows of the F4 injection test) |
| `docs/governance/glossary.md` | dbt seed (17 terms) | Business metadata |
| `docs/governance/raci.md` | dbt seed (28 datasets) | Ownership matrix with institution owners |
| `docs/governance/dq_rules.md` | `config/dq_rules.yml` (27 rules) | Rule catalog, auto-generated |
| `docs/lineage.md` | dbt `manifest.json` | Mermaid diagram, external→bronze→silver→gold |
| `docs/data_dictionary.md` | manifest + catalog | Column types, descriptions, tests, owners |
| `docs/governance/retention_policy.md` | `policies.py` generator | TTL/quarantine/silver-gold retention |
| `docs/governance/dama_mapping.md` | `policies.py` generator | 11 DAMA-DMBOK knowledge areas |
| `docs/governance/incident_log.md` | Manual | 4 documented incidents |
