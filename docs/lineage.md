# Data Lineage

Generated from `dbt/panganwatch/target/manifest.json` plus manual external → bronze → canonical mappings.

## External Sources → Bronze → Canonical Tables

| External source | Bronze collection | Canonical table/model |
|---|---|---|
| BPS WebAPI | `bronze.bps_inflation` | `silver.inflasi_kota` |
| HDX WFP | `bronze.hdx_wfp_prices` | `silver.harga_pangan` |
| Open-Meteo Archive | `bronze.open_meteo_daily` | `silver.cuaca_harian` |
| Open-Meteo Current | `bronze.open_meteo_current` | `silver.cuaca_terkini` |
| PIHPS/Panel Harga | `bronze.pihps_prices` | `silver.harga_pangan` |
| Wilayah source files | `bronze.wilayah_raw` | `ref.ref_provinsi` |

## dbt Sources

| Source node | Relation | Description |
|---|---|---|
| `source.panganwatch.governance.dq_results` | `governance.dq_results` | Aggregated results per DQ rule per run (F4). |
| `source.panganwatch.governance.pipeline_runs` | `governance.pipeline_runs` | Execution log for every ingestion job (F1/F3). |
| `source.panganwatch.governance.quarantine` | `governance.quarantine` | Records that failed an error-severity DQ rule (F4). |
| `source.panganwatch.silver.cuaca_harian` | `silver.cuaca_harian` | Daily historical weather per province (F3c, Open-Meteo Archive). |
| `source.panganwatch.silver.harga_pangan` | `silver.harga_pangan` | Food prices per date x province x commodity x market type x source (F3a). |
| `source.panganwatch.silver.inflasi_kota` | `silver.inflasi_kota` | Monthly IHK and inflation per BPS IHK city (F3b, BPS WebAPI var 2245/2249, DEC-039). |

## Gold Model Upstream Summary

| Gold model | Materialization | Direct upstream nodes |
|---|---|---|
| `gold.dim_komoditas` | table | `staging.stg_ref_komoditas` |
| `gold.dim_provinsi` | table | `staging.stg_ref_provinsi` |
| `gold.dim_tanggal` | table | `staging.stg_cuaca_harian`, `staging.stg_harga_pangan` |
| `gold.fct_harga_bulanan` | incremental | `staging.stg_harga_pangan` |
| `gold.mart_cuaca_harga_bulanan` | table | `gold.dim_komoditas`, `gold.fct_harga_bulanan`, `staging.stg_cuaca_harian` |
| `gold.mart_disparitas_provinsi` | table | `gold.fct_harga_bulanan` |
| `gold.mart_dq_scorecard` | table | `staging.stg_dq_results` |
| `gold.mart_inflasi_vs_harga` | table | `gold.dim_provinsi`, `gold.fct_harga_bulanan`, `staging.stg_inflasi_kota` |

## Diagram Alur Data

```mermaid
flowchart LR
    n_bronze_bps_inflation["bronze.bps_inflation"]
    n_bronze_hdx_wfp_prices["bronze.hdx_wfp_prices"]
    n_bronze_open_meteo_current["bronze.open_meteo_current"]
    n_bronze_open_meteo_daily["bronze.open_meteo_daily"]
    n_bronze_pihps_prices["bronze.pihps_prices"]
    n_bronze_wilayah_raw["bronze.wilayah_raw"]
    n_external_BPS_WebAPI["external.BPS WebAPI"]
    n_external_HDX_WFP["external.HDX WFP"]
    n_external_Open_Meteo_Archive["external.Open-Meteo Archive"]
    n_external_Open_Meteo_Current["external.Open-Meteo Current"]
    n_external_PIHPS_Panel_Harga["external.PIHPS/Panel Harga"]
    n_external_Wilayah_source_files["external.Wilayah source files"]
    n_gold_dim_komoditas["gold.dim_komoditas"]
    n_gold_dim_provinsi["gold.dim_provinsi"]
    n_gold_dim_tanggal["gold.dim_tanggal"]
    n_gold_fct_harga_bulanan["gold.fct_harga_bulanan"]
    n_gold_mart_cuaca_harga_bulanan["gold.mart_cuaca_harga_bulanan"]
    n_gold_mart_disparitas_provinsi["gold.mart_disparitas_provinsi"]
    n_gold_mart_dq_scorecard["gold.mart_dq_scorecard"]
    n_gold_mart_inflasi_vs_harga["gold.mart_inflasi_vs_harga"]
    n_governance_dq_results["governance.dq_results"]
    n_governance_pipeline_runs["governance.pipeline_runs"]
    n_governance_quarantine["governance.quarantine"]
    n_ref_governance_glossary["ref.governance_glossary"]
    n_ref_governance_raci["ref.governance_raci"]
    n_ref_ref_crosswalk_wilayah["ref.ref_crosswalk_wilayah"]
    n_ref_ref_ihk_kota["ref.ref_ihk_kota"]
    n_ref_ref_kabkota["ref.ref_kabkota"]
    n_ref_ref_komoditas["ref.ref_komoditas"]
    n_ref_ref_komoditas_alias["ref.ref_komoditas_alias"]
    n_ref_ref_provinsi["ref.ref_provinsi"]
    n_ref_ref_provinsi_alias["ref.ref_provinsi_alias"]
    n_silver_cuaca_harian["silver.cuaca_harian"]
    n_silver_cuaca_terkini["silver.cuaca_terkini"]
    n_silver_harga_pangan["silver.harga_pangan"]
    n_silver_inflasi_kota["silver.inflasi_kota"]
    n_staging_stg_cuaca_harian["staging.stg_cuaca_harian"]
    n_staging_stg_dq_results["staging.stg_dq_results"]
    n_staging_stg_harga_pangan["staging.stg_harga_pangan"]
    n_staging_stg_inflasi_kota["staging.stg_inflasi_kota"]
    n_staging_stg_ref_komoditas["staging.stg_ref_komoditas"]
    n_staging_stg_ref_provinsi["staging.stg_ref_provinsi"]
    n_staging_stg_ref_provinsi_alias["staging.stg_ref_provinsi_alias"]

    n_bronze_bps_inflation --> n_silver_inflasi_kota
    n_bronze_hdx_wfp_prices --> n_silver_harga_pangan
    n_bronze_open_meteo_current --> n_silver_cuaca_terkini
    n_bronze_open_meteo_daily --> n_silver_cuaca_harian
    n_bronze_pihps_prices --> n_silver_harga_pangan
    n_bronze_wilayah_raw --> n_ref_ref_provinsi
    n_external_BPS_WebAPI --> n_bronze_bps_inflation
    n_external_HDX_WFP --> n_bronze_hdx_wfp_prices
    n_external_Open_Meteo_Archive --> n_bronze_open_meteo_daily
    n_external_Open_Meteo_Current --> n_bronze_open_meteo_current
    n_external_PIHPS_Panel_Harga --> n_bronze_pihps_prices
    n_external_Wilayah_source_files --> n_bronze_wilayah_raw
    n_gold_dim_komoditas --> n_gold_mart_cuaca_harga_bulanan
    n_gold_dim_provinsi --> n_gold_mart_inflasi_vs_harga
    n_gold_fct_harga_bulanan --> n_gold_mart_cuaca_harga_bulanan
    n_gold_fct_harga_bulanan --> n_gold_mart_disparitas_provinsi
    n_gold_fct_harga_bulanan --> n_gold_mart_inflasi_vs_harga
    n_governance_dq_results --> n_staging_stg_dq_results
    n_ref_ref_ihk_kota --> n_staging_stg_inflasi_kota
    n_silver_cuaca_harian --> n_staging_stg_cuaca_harian
    n_silver_harga_pangan --> n_staging_stg_harga_pangan
    n_silver_inflasi_kota --> n_staging_stg_inflasi_kota
    n_staging_stg_cuaca_harian --> n_gold_dim_tanggal
    n_staging_stg_cuaca_harian --> n_gold_mart_cuaca_harga_bulanan
    n_staging_stg_dq_results --> n_gold_mart_dq_scorecard
    n_staging_stg_harga_pangan --> n_gold_dim_tanggal
    n_staging_stg_harga_pangan --> n_gold_fct_harga_bulanan
    n_staging_stg_inflasi_kota --> n_gold_mart_inflasi_vs_harga
    n_staging_stg_ref_komoditas --> n_gold_dim_komoditas
    n_staging_stg_ref_provinsi --> n_gold_dim_provinsi
```
