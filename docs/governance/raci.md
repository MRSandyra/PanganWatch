# RACI Matrix

Generated from `dbt\panganwatch\seeds\governance_raci.csv` — **28 datasets** × 4 roles

| Dataset | Data Owner | Data Steward | Data Custodian | Consumer |
|---|---|---|---|---|
| bps_inflation (bronze) | A (BPS) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.dim_komoditas | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.dim_provinsi | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.dim_tanggal | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.fct_harga_bulanan | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.mart_cuaca_harga_bulanan | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.mart_disparitas_provinsi | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| gold.mart_dq_scorecard | A (PanganWatch analytics) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Governance consumers) |
| governance.dq_results | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Data quality consumers) |
| governance.pipeline_runs | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Platform operators) |
| governance.quarantine | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Data quality consumers) |
| governance.weather_alerts | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Streaming consumers) |
| governance_glossary | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| governance_raci | A (PanganWatch governance) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| hdx_wfp_prices (bronze) | A (WFP) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| open_meteo_current (bronze) | A (Open-Meteo) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Streaming consumers) |
| open_meteo_daily (bronze) | A (Open-Meteo) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| pihps_prices (bronze) | A (Bapanas/Panel Harga) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| ref.ref_crosswalk_wilayah | A (PanganWatch reference data) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| ref.ref_kabkota | A (Kemendagri/BPS) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| ref.ref_komoditas | A (PanganWatch reference data) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| ref.ref_komoditas_alias | A (PanganWatch reference data) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| ref.ref_provinsi | A (Kemendagri/BPS) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| ref.ref_provinsi_alias | A (PanganWatch reference data) | R (PanganWatch data steward) | C (PanganWatch platform) | I (All users) |
| silver.cuaca_harian | A (PanganWatch data owner) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| silver.cuaca_terkini | A (PanganWatch data owner) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Streaming consumers) |
| silver.harga_pangan | A (PanganWatch data owner) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Analytics users) |
| wilayah_raw (bronze) | A (Kemendagri/BPS/Open-Meteo Geocoding) | R (PanganWatch data steward) | C (PanganWatch platform) | I (Reference data users) |