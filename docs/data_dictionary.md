# Data Dictionary

Generated from `dbt/panganwatch/target/manifest.json`, `catalog.json`, and `dbt/panganwatch/seeds/governance_raci.csv`.

## Tables and Columns

### governance.dq_results

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch governance  
**Description:** Aggregated results per DQ rule per run (F4).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| checked_at | timestamp with time zone |  |  |
| column_name | text |  |  |
| dataset | text |  |  |
| dimension | text |  |  |
| id | bigint |  |  |
| pass_rate | numeric(5,2) |  |  |
| rows_checked | integer |  |  |
| rows_failed | integer |  |  |
| rule_id | text |  |  |
| run_id | text |  |  |
| severity | text |  |  |

### governance.pipeline_runs

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch governance  
**Description:** Execution log for every ingestion job (F1/F3).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| completed_at | timestamp with time zone |  |  |
| error_message | text |  |  |
| id | bigint |  |  |
| rows_failed | integer |  |  |
| rows_processed | integer |  |  |
| rows_success | integer |  |  |
| run_id | text |  |  |
| source | text |  |  |
| started_at | timestamp with time zone |  |  |
| status | text |  |  |

### governance.quarantine

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch governance  
**Description:** Records that failed an error-severity DQ rule (F4).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| dataset | text |  |  |
| id | bigint |  |  |
| natural_key | jsonb |  |  |
| quarantined_at | timestamp with time zone |  |  |
| reason | text |  |  |
| record | jsonb |  |  |
| resolution_note | text |  |  |
| resolved_at | timestamp with time zone |  |  |
| rule_id | text |  |  |
| run_id | text |  |  |

### silver.cuaca_harian

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch data owner  
**Description:** Daily historical weather per province (F3c, Open-Meteo Archive).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| id | bigint |  |  |
| kode_provinsi_bps | character varying(2) |  |  |
| loaded_at | timestamp with time zone |  |  |
| precipitation_mm | numeric(6,2) |  |  |
| run_id | text |  |  |
| source | text |  |  |
| tanggal | date |  |  |
| tmax_c | numeric(5,2) |  |  |
| tmin_c | numeric(5,2) |  |  |

### silver.harga_pangan

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch data owner  
**Description:** Food prices per date x province x commodity x market type x source (F3a).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| harga | numeric(12,2) |  |  |
| id | bigint |  |  |
| jenis_pasar | text |  |  |
| kode_kabkota_bps | character varying(6) |  |  |
| kode_provinsi_bps | character varying(2) |  |  |
| komoditas_id | character varying(4) |  |  |
| loaded_at | timestamp with time zone |  |  |
| run_id | text |  |  |
| satuan | text |  |  |
| source | text |  |  |
| tanggal | date |  |  |

### silver.inflasi_kota

**Resource type:** source  
**Materialization/type:** source  
**Owner:** PanganWatch data platform  
**Description:** Monthly IHK and inflation per BPS IHK city (F3b, BPS WebAPI var 2245/2249, DEC-039).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| bulan | date |  |  |
| ihk | numeric(10,2) |  |  |
| inflasi_mtm | numeric(8,2) |  |  |
| inflasi_yoy | numeric(8,2) |  |  |
| kode_vervar | integer |  |  |
| loaded_at | timestamp with time zone |  |  |
| nama_kota | text |  |  |
| run_id | text |  |  |
| source | text |  |  |

### ref.governance_glossary

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch governance  
**Description:** Governance term glossary (at least 15 terms) for F8a  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| definition | text |  | not_null_governance_glossary_definition |
| domain | character varying(50) |  | not_null_governance_glossary_domain |
| owner | character varying(50) |  | not_null_governance_glossary_owner |
| related_columns | character varying(200) |  |  |
| source | character varying(50) |  |  |
| term | character varying(100) |  | not_null_governance_glossary_term, unique_governance_glossary_term |

### ref.governance_raci

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch governance  
**Description:** RACI matrix for dataset x role (Data Owner, Data Steward, Data Custodian, Consumer) for F8a  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| dataset | character varying(100) |  | not_null_governance_raci_dataset |
| owner | character varying(200) |  |  |
| raci_value | character varying(1) |  | accepted_values_governance_raci_raci_value__R__A__C__I, not_null_governance_raci_raci_value |
| role | character varying(50) |  | not_null_governance_raci_role |

### ref.ref_crosswalk_wilayah

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch reference data  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| alasan | text |  |  |
| kode_bps | double precision |  |  |
| match_method | text |  |  |
| nama_sumber | text |  |  |
| sumber | text |  |  |

### ref.ref_ihk_kota

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch reference data  
**Description:** Maps the 150 BPS IHK cities (var 2245) to kab/kota and province (F3b). Built by scripts/build_ref_ihk_kota.py from ref_kabkota; manual mappings and unmapped cities are reported in docs/governance/ihk_mapping_report.md.  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| alasan | character varying(300) |  | not_null_ref_ihk_kota_alasan |
| kode_kabkota_bps | character varying(6) |  | relationships_ref_ihk_kota_kode_kabkota_bps__kode_bps__ref_ref_kabkota_ |
| kode_provinsi_bps | character varying(2) |  | relationships_ref_ihk_kota_kode_provinsi_bps__kode_bps__ref_ref_provinsi_ |
| kode_vervar | integer |  | not_null_ref_ihk_kota_kode_vervar, unique_ref_ihk_kota_kode_vervar |
| match_method | character varying(20) |  | accepted_values_ref_ihk_kota_match_method__exact_code__exact_name__normalized_name__manual |
| nama_bps | character varying(100) |  | not_null_ref_ihk_kota_nama_bps, unique_ref_ihk_kota_nama_bps |

### ref.ref_kabkota

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** Kemendagri/BPS  
**Description:** 513 Indonesian kab/kota — BPS/Kemendagri code (4-digit prov.kab), name, province code  
**Table tests:** prov_kab_unique_ref_kabkota_kode_bps__kode_provinsi_bps  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| kode_bps | character varying(6) |  | not_null_ref_kabkota_kode_bps, unique_ref_kabkota_kode_bps |
| kode_kemendagri | character varying(6) |  | not_null_ref_kabkota_kode_kemendagri, unique_ref_kabkota_kode_kemendagri |
| kode_provinsi_bps | character varying(2) |  | not_null_ref_kabkota_kode_provinsi_bps |
| nama | character varying(100) |  | not_null_ref_kabkota_nama |

### ref.ref_komoditas

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch reference data  
**Description:** 14 Indonesian reference commodities — code, canonical name, group, unit, HET  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| het | numeric(10,2) |  |  |
| kelompok | character varying(20) |  | accepted_values_ref_komoditas_kelompok__beras__cabai__bawang__daging__gula__minyak__telur, not_null_ref_komoditas_kelompok |
| komoditas_id | character varying(4) |  | not_null_ref_komoditas_komoditas_id, relationships_ref_komoditas_alias_komoditas_id__komoditas_id__ref_ref_komoditas_, unique_ref_komoditas_komoditas_id |
| nama_kanonis | character varying(50) |  | not_null_ref_komoditas_nama_kanonis, unique_ref_komoditas_nama_kanonis |
| satuan | character varying(10) |  | not_null_ref_komoditas_satuan |

### ref.ref_komoditas_alias

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch reference data  
**Description:** Maps source names to komoditas_id  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| alasan | character varying(200) |  | not_null_ref_komoditas_alias_alasan |
| komoditas_id | character varying(4) |  | not_null_ref_komoditas_alias_komoditas_id, relationships_ref_komoditas_alias_komoditas_id__komoditas_id__ref_ref_komoditas_ |
| match_method | character varying(20) |  | accepted_values_ref_komoditas_alias_match_method__exact_name__normalized_name__manual, not_null_ref_komoditas_alias_match_method |
| nama_sumber | character varying(100) |  | not_null_ref_komoditas_alias_nama_sumber, unique_ref_komoditas_alias_nama_sumber |
| sumber | character varying(20) |  | accepted_values_ref_komoditas_alias_sumber__PIHPS__HDX__BPS__Kemendagri, not_null_ref_komoditas_alias_sumber |

### ref.ref_provinsi

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** Kemendagri/BPS  
**Description:** 38 Indonesian provinces — BPS/Kemendagri code, name, capital, coordinates  
**Table tests:** bbox_indonesia_ref_provinsi_lat__lon  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| ibu_kota | character varying(64) |  | not_null_ref_provinsi_ibu_kota |
| kode_bps | character varying(2) |  | not_null_ref_provinsi_kode_bps, relationships_ref_provinsi_alias_kode_bps__kode_bps__ref_ref_provinsi_, unique_ref_provinsi_kode_bps |
| kode_kemendagri | character varying(2) |  | not_null_ref_provinsi_kode_kemendagri, unique_ref_provinsi_kode_kemendagri |
| lat | double precision |  | not_null_ref_provinsi_lat |
| lon | double precision |  | not_null_ref_provinsi_lon |
| nama_provinsi | character varying(64) |  | not_null_ref_provinsi_nama_provinsi |
| source | character varying(200) |  |  |

### ref.ref_provinsi_alias

**Resource type:** seed  
**Materialization/type:** seed  
**Owner:** PanganWatch reference data  
**Description:** Maps province names as written in the source data (e.g. HDX WFP admin1) to ref_provinsi.kode_bps (F3a)  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| alasan | character varying(300) |  | not_null_ref_provinsi_alias_alasan |
| kode_bps | character varying(2) |  | not_null_ref_provinsi_alias_kode_bps, relationships_ref_provinsi_alias_kode_bps__kode_bps__ref_ref_provinsi_ |
| match_method | character varying(20) |  | accepted_values_ref_provinsi_alias_match_method__exact_name__normalized_name__manual, not_null_ref_provinsi_alias_match_method |
| nama_sumber | character varying(100) |  | not_null_ref_provinsi_alias_nama_sumber, unique_ref_provinsi_alias_nama_sumber |
| sumber | character varying(20) |  | accepted_values_ref_provinsi_alias_sumber__PIHPS__HDX__BPS__Kemendagri, not_null_ref_provinsi_alias_sumber |

### staging.stg_cuaca_harian

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for silver.cuaca_harian with cleaned weather data  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| id | bigint | Primary key | not_null_stg_cuaca_harian_id, unique_stg_cuaca_harian_id |
| kode_provinsi_bps | character varying(2) | BPS province code (2 digits) | not_null_stg_cuaca_harian_kode_provinsi_bps |
| loaded_at | timestamp with time zone | Timestamp when loaded into silver | not_null_stg_cuaca_harian_loaded_at |
| precipitation_mm | numeric(6,2) | Daily rainfall (mm) |  |
| run_id | text | Pipeline run ID | not_null_stg_cuaca_harian_run_id |
| source | text | Data source (open-meteo) | not_null_stg_cuaca_harian_source |
| tanggal | date | Weather observation date | not_null_stg_cuaca_harian_tanggal |
| tmax_c | numeric(5,2) | Daily maximum temperature (Celsius) |  |
| tmin_c | numeric(5,2) | Daily minimum temperature (Celsius) |  |

### staging.stg_dq_results

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for governance.dq_results (aggregated DQ rule results per run, F4).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| checked_at | timestamp with time zone | When this rule was run | not_null_stg_dq_results_checked_at |
| dataset | text | Dataset checked (e.g. silver.harga_pangan) | not_null_stg_dq_results_dataset |
| dimension | text | DAMA dimension (completeness, validity, accuracy, consistency, timeliness, uniqueness) | not_null_stg_dq_results_dimension |
| id | bigint | Primary key | not_null_stg_dq_results_id, unique_stg_dq_results_id |
| pass_rate | numeric(5,2) | Percentage of rows that passed (0-100) |  |
| rows_checked | integer | Number of rows this rule checked | not_null_stg_dq_results_rows_checked |
| rows_failed | integer | Number of rows that failed this rule | not_null_stg_dq_results_rows_failed |
| rule_id | text | DQ rule ID (config/dq_rules.yml) | not_null_stg_dq_results_rule_id |
| run_id | text | Pipeline run ID that produced this DQ row | not_null_stg_dq_results_run_id |
| severity | text | error or warn | not_null_stg_dq_results_severity |

### staging.stg_harga_pangan

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for silver.harga_pangan with cleaned and normalized data  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| harga | numeric(12,2) | Price in rupiah | not_null_stg_harga_pangan_harga |
| id | bigint | Primary key | not_null_stg_harga_pangan_id, unique_stg_harga_pangan_id |
| jenis_pasar | text | Market type (Tradisional/Modern/Swasta) | not_null_stg_harga_pangan_jenis_pasar |
| kode_kabkota_bps | character varying(6) | BPS kab/kota code (6 digits), nullable |  |
| kode_provinsi_bps | character varying(2) | BPS province code (2 digits) | not_null_stg_harga_pangan_kode_provinsi_bps |
| komoditas_id | character varying(4) | Commodity code (4 digits) | not_null_stg_harga_pangan_komoditas_id |
| loaded_at | timestamp with time zone | Timestamp when loaded into silver | not_null_stg_harga_pangan_loaded_at |
| run_id | text | Pipeline run ID | not_null_stg_harga_pangan_run_id |
| satuan | text | Price unit (Rp/kg, Rp/liter, etc.) | not_null_stg_harga_pangan_satuan |
| source | text | Data source (HDX WFP, PIHPS, BPS) | not_null_stg_harga_pangan_source |
| tanggal | date | Price date | not_null_stg_harga_pangan_tanggal |

### staging.stg_inflasi_kota

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging for silver.inflasi_kota (BPS city IHK/inflation, F3b) plus the IHK city -> kab/kota -> province mapping via the ref_ihk_kota seed. Cities that couldn't be mapped still appear, with kode_provinsi_bps NULL (reported by the assert_ihk_kota_all_mapped test).
  
**Table tests:** assert_ihk_kota_all_mapped, dbt_utils_unique_combination_of_columns_stg_inflasi_kota_bulan__kode_vervar  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| bulan | date | Observation month (the 1st of that month). | not_null_stg_inflasi_kota_bulan |
| ihk | numeric(10,2) | City Consumer Price Index (2022=100). | not_null_stg_inflasi_kota_ihk |
| inflasi_mtm | numeric(8,2) | Month-to-month inflation (%), computed from consecutive IHK values; NULL for the first month in the series. |  |
| inflasi_yoy | numeric(8,2) | Year-on-year inflation (%) as published by BPS (var 2249). |  |
| kode_kabkota_bps | character varying(6) | BPS kab/kota code from the ref_ihk_kota mapping (NULL for KOTA JAKARTA, which maps to a province). |  |
| kode_provinsi_bps | character varying(2) | BPS province code from the ref_ihk_kota mapping (NULL if the city could not be mapped). | relationships_stg_inflasi_kota_kode_provinsi_bps__kode_bps__ref_stg_ref_provinsi_ |
| kode_vervar | integer | City id in BPS variable 2245 (not a region code). | not_null_stg_inflasi_kota_kode_vervar |
| loaded_at | timestamp with time zone | Timestamp when loaded into silver |  |
| match_method | character varying(20) | City mapping method (normalized_name or manual). |  |
| nama_kota | text | IHK city name as published by BPS (e.g. KOTA MEDAN, MEULABOH). | not_null_stg_inflasi_kota_nama_kota |
| run_id | text | Pipeline run ID |  |

### staging.stg_ref_komoditas

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for ref.ref_komoditas with commodity reference data  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| het | numeric(10,2) | Harga Eceran Tertinggi (ceiling retail price) |  |
| kelompok | character varying(20) | Commodity group | not_null_stg_ref_komoditas_kelompok |
| komoditas_id | character varying(4) | Commodity code (4 digits) | not_null_stg_ref_komoditas_komoditas_id, unique_stg_ref_komoditas_komoditas_id |
| nama_kanonis | character varying(50) | Canonical commodity name | not_null_stg_ref_komoditas_nama_kanonis |
| satuan | character varying(10) | Standard unit | not_null_stg_ref_komoditas_satuan |

### staging.stg_ref_provinsi

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for ref.ref_provinsi with province reference data  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| ibu_kota | character varying(64) | Province capital |  |
| kode_bps | character varying(2) | BPS province code (2 digits) | not_null_stg_ref_provinsi_kode_bps, unique_stg_ref_provinsi_kode_bps |
| kode_kemendagri | character varying(2) | Kemendagri province code |  |
| lat | double precision | Latitude |  |
| lon | double precision | Longitude |  |
| nama_provinsi | character varying(64) | Official province name | not_null_stg_ref_provinsi_nama_provinsi |
| source | character varying(200) | Data source | not_null_stg_ref_provinsi_source |

### staging.stg_ref_provinsi_alias

**Resource type:** model  
**Materialization/type:** view  
**Owner:** PanganWatch  
**Description:** Staging model for ref.ref_provinsi_alias mapping source names to BPS codes  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| alasan | character varying(300) | Reason for the match |  |
| kode_bps | character varying(2) | BPS province code (2 digits) | not_null_stg_ref_provinsi_alias_kode_bps |
| match_method | character varying(20) | Matching method (normalized_name, manual) | not_null_stg_ref_provinsi_alias_match_method |
| nama_sumber | character varying(100) | Province name as it appears in the external source | not_null_stg_ref_provinsi_alias_nama_sumber |
| sumber | character varying(20) | Source name (HDX, PIHPS, BPS) | not_null_stg_ref_provinsi_alias_sumber |

### gold.dim_komoditas

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Commodity dimension (1 row per commodity), from the ref.ref_komoditas seed (F2).  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| het | numeric(10,2) | Harga Eceran Tertinggi (ceiling retail price), nullable — only set when an official HET source is found (F2). |  |
| kelompok | character varying(20) | Strategic commodity group. | accepted_values_dim_komoditas_kelompok__beras__cabai__bawang__daging__gula__minyak__telur, not_null_dim_komoditas_kelompok |
| komoditas_id | character varying(4) | Commodity code (4 digits), primary key. | not_null_dim_komoditas_komoditas_id, relationships_fct_harga_bulanan_komoditas_id__komoditas_id__ref_dim_komoditas_, relationships_mart_disparitas_provinsi_komoditas_id__komoditas_id__ref_dim_komoditas_, unique_dim_komoditas_komoditas_id |
| nama_kanonis | character varying(50) | Canonical commodity name (e.g. 'beras', 'cabai rawit'). | not_null_dim_komoditas_nama_kanonis |
| satuan | character varying(10) | Standard unit (kg, liter, item). | not_null_dim_komoditas_satuan |

### gold.dim_provinsi

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Province dimension (1 row per province), from the ref.ref_provinsi seed (F2).  
**Table tests:** assert_disparitas_provinces_exist_in_dim_provinsi  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| ibu_kota | character varying(64) | Name of the province capital. | not_null_dim_provinsi_ibu_kota |
| kode_kemendagri | character varying(2) | Kemendagri province code (nullable if the source is unavailable, see the F2 fallback). |  |
| kode_provinsi_bps | character varying(2) | BPS province code (2 digits), primary key. | not_null_dim_provinsi_kode_provinsi_bps, relationships_fct_harga_bulanan_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_, relationships_mart_cuaca_harga_bulanan_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_, relationships_mart_disparitas_provinsi_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_, relationships_mart_inflasi_vs_harga_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_, unique_dim_provinsi_kode_provinsi_bps |
| lat | double precision | Latitude of the province capital (decimal degrees). | not_null_dim_provinsi_lat |
| lon | double precision | Longitude of the province capital (decimal degrees). | not_null_dim_provinsi_lon |
| nama_provinsi | character varying(64) | Official province name. | not_null_dim_provinsi_nama_provinsi |

### gold.dim_tanggal

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Date dimension (1 row per calendar date), spanning the union of the silver.harga_pangan and silver.cuaca_harian date ranges.  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| awal_minggu | date | Monday (start) of the ISO week containing `tanggal`. | not_null_dim_tanggal_awal_minggu |
| bulan | integer | Month number (1-12). | not_null_dim_tanggal_bulan |
| is_weekend | boolean | True if the date falls on Saturday/Sunday. | not_null_dim_tanggal_is_weekend |
| minggu_iso | text | ISO 8601 week (format YYYY-Www). | not_null_dim_tanggal_minggu_iso |
| tahun | integer | Calendar year. | not_null_dim_tanggal_tahun |
| tanggal | date | Calendar date, primary key. | not_null_dim_tanggal_tanggal, unique_dim_tanggal_tanggal |

### gold.fct_harga_bulanan

**Resource type:** model  
**Materialization/type:** incremental  
**Owner:** PanganWatch analytics  
**Description:** Food-price fact table, grain date x province x commodity x jenis_pasar x source. Named "bulanan" (not "harian" like fct_harga_harian in Appendix B) because the price source (HDX WFP) is monthly-grain — every `tanggal` value is a monthly snapshot date (DEC-010). Incremental materialization with a composite unique_key.
  
**Table tests:** dbt_utils_unique_combination_of_columns_fct_harga_bulanan_tanggal__kode_provinsi_bps__komoditas_id__jenis_pasar__source  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| harga_max | numeric | Maximum price for this key on this date. | dbt_utils_accepted_range_fct_harga_bulanan_harga_max__False__1000000__0, not_null_fct_harga_bulanan_harga_max |
| harga_median | double precision | Median price for this key on this date. | dbt_utils_accepted_range_fct_harga_bulanan_harga_median__False__1000000__0, not_null_fct_harga_bulanan_harga_median |
| harga_min | numeric | Minimum price for this key on this date. | dbt_utils_accepted_range_fct_harga_bulanan_harga_min__False__1000000__0, not_null_fct_harga_bulanan_harga_min |
| jenis_pasar | text | Market type/name from the data source. | not_null_fct_harga_bulanan_jenis_pasar |
| kode_provinsi_bps | character varying(2) | BPS province code. Kab/kota rows are aggregated to province (median) — the HDX source's kode_kabkota_bps is always NULL. | not_null_fct_harga_bulanan_kode_provinsi_bps, relationships_fct_harga_bulanan_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_ |
| komoditas_id | character varying(4) | Commodity code. | not_null_fct_harga_bulanan_komoditas_id, relationships_fct_harga_bulanan_komoditas_id__komoditas_id__ref_dim_komoditas_ |
| n_dq_warn | integer | Number of 'warn'-severity DQ flags on the rows aggregated into this one. Currently always 0 (a placeholder) because the F4 rule engine does not yet write a per-row DQ flag on silver rows; this is not a fabricated value, just not implemented yet.
 | not_null_fct_harga_bulanan_n_dq_warn |
| n_observasi | bigint | Number of silver.harga_pangan rows aggregated into this row. | not_null_fct_harga_bulanan_n_observasi |
| source | text | Price source (e.g. 'HDX WFP'). | not_null_fct_harga_bulanan_source |
| tanggal | date | Price snapshot date. | not_null_fct_harga_bulanan_tanggal |

### gold.mart_cuaca_harga_bulanan

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Weather and price combined, per month x province x commodity group. Named "bulanan" (not "mingguan" like mart_cuaca_harga_mingguan in Appendix B) because the price grain is monthly (DEC-010). The chili/shallot-vs-rain lag is computed separately in Python (F9) from daily silver.cuaca_harian.
  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| bulan | date | Month (the 1st of that month). | not_null_mart_cuaca_harga_bulanan_bulan |
| harga_median | double precision | Median of fct_harga_bulanan's harga_median for this group in this month. | dbt_utils_accepted_range_mart_cuaca_harga_bulanan_harga_median__False__1000000__0 |
| hari_hujan_lebat | bigint | Number of days in the month with precipitation_mm >= 50mm (the starting threshold for BMKG's 'heavy' category, config/settings.yaml, DEC-013). | dbt_utils_accepted_range_mart_cuaca_harga_bulanan_hari_hujan_lebat__31__0 |
| kelompok | character varying(20) | Commodity group (beras, cabai, bawang, daging, gula, minyak, telur). | accepted_values_mart_cuaca_harga_bulanan_kelompok__beras__cabai__bawang__daging__gula__minyak__telur, not_null_mart_cuaca_harga_bulanan_kelompok |
| kode_provinsi_bps | character varying(2) | BPS province code. | not_null_mart_cuaca_harga_bulanan_kode_provinsi_bps, relationships_mart_cuaca_harga_bulanan_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_ |
| pct_change_mom | numeric | Percentage change in harga_median vs. the previous month (same group+province). |  |
| total_hujan_mm | numeric | Total rainfall for the month (mm). |  |

### gold.mart_disparitas_provinsi

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Province price disparity vs. the national median, grain month x province x commodity. Grain is "month" (not "week" per Appendix B) because the price source is monthly-grain (DEC-010).
  
**Table tests:** assert_disparitas_provinces_exist_in_dim_provinsi, assert_no_negative_national_median  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| bulan | date | Month (the 1st of that month). | not_null_mart_disparitas_provinsi_bulan |
| harga_median_nasional | double precision | National median = the median of harga_median_provinsi across all provinces for this month+commodity. | not_null_mart_disparitas_provinsi_harga_median_nasional |
| harga_median_provinsi | double precision | This province's median price for this month (the median of fct_harga_bulanan's harga_median). | not_null_mart_disparitas_provinsi_harga_median_provinsi |
| kode_provinsi_bps | character varying(2) | BPS province code. | not_null_mart_disparitas_provinsi_kode_provinsi_bps, relationships_mart_disparitas_provinsi_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_ |
| komoditas_id | character varying(4) | Commodity code. | not_null_mart_disparitas_provinsi_komoditas_id, relationships_mart_disparitas_provinsi_komoditas_id__komoditas_id__ref_dim_komoditas_ |
| pct_deviasi | numeric | (province - national) / national x 100. | dbt_utils_accepted_range_mart_disparitas_provinsi_pct_deviasi__1000___100 |
| rank_deviasi | bigint | Province rank by absolute deviation from the national median (1 = most deviant). | not_null_mart_disparitas_provinsi_rank_deviasi |

### gold.mart_dq_scorecard

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** Data quality scorecard per run date x source x DAMA dimension, from governance.dq_results (F4). The "source" column is mapped from `dataset` in dq_results (see the model SQL).
  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| dimensi | text | DAMA dimension. | accepted_values_mart_dq_scorecard_dimensi__completeness__validity__accuracy__consistency__timeliness__uniqueness, not_null_mart_dq_scorecard_dimensi |
| rows_checked | bigint | Total rows checked (summed across rules). | not_null_mart_dq_scorecard_rows_checked |
| rows_failed | bigint | Total rows that failed (summed across rules). | not_null_mart_dq_scorecard_rows_failed |
| rules_passed | bigint | Number of rules with 0 failed rows (rows_failed=0). | not_null_mart_dq_scorecard_rules_passed |
| rules_total | bigint | Number of distinct rules active for this dataset+dimension on tanggal_run. | not_null_mart_dq_scorecard_rules_total |
| score | numeric | 100 x (rows_checked - rows_failed) / rows_checked. | dbt_utils_accepted_range_mart_dq_scorecard_score__100__0 |
| source | text | Dataset checked (e.g. silver.harga_pangan). | not_null_mart_dq_scorecard_source |
| tanggal_run | date | Date the DQ rules were run. | not_null_mart_dq_scorecard_tanggal_run |

### gold.mart_inflasi_vs_harga

**Resource type:** model  
**Materialization/type:** table  
**Owner:** PanganWatch analytics  
**Description:** City inflation (BPS IHK) paired with the food-price change in that city's province, grain month x city (Appendix B). HDX WFP food prices only cover 34 provinces and 2025-06..2026-06 (January 2026 is partial), so pct_change_harga_pangan is NULL outside that window. Correlation, not causation.
  
**Table tests:** dbt_utils_unique_combination_of_columns_mart_inflasi_vs_harga_bulan__kode_vervar  

| Column | Data Type | Description | Tests |
|---|---|---|---|
| bulan | date | Inflation observation month (the 1st of that month). | not_null_mart_inflasi_vs_harga_bulan |
| ihk | numeric(10,2) | City Consumer Price Index (2022=100). | not_null_mart_inflasi_vs_harga_ihk |
| inflasi_mtm | numeric(8,2) | Month-to-month inflation (%), computed from consecutive IHK values (NULL for the first month in the series). | dbt_utils_accepted_range_mart_inflasi_vs_harga_inflasi_mtm__50___20 |
| inflasi_yoy | numeric(8,2) | Year-on-year inflation (%) from BPS (var 2249). | dbt_utils_accepted_range_mart_inflasi_vs_harga_inflasi_yoy__50___20 |
| kode_provinsi_bps | character varying(2) | BPS province code from the city mapping (ref_ihk_kota). | not_null_mart_inflasi_vs_harga_kode_provinsi_bps, relationships_mart_inflasi_vs_harga_kode_provinsi_bps__kode_provinsi_bps__ref_dim_provinsi_ |
| kode_vervar | integer | City id in BPS variable 2245. | not_null_mart_inflasi_vs_harga_kode_vervar |
| n_komoditas | bigint | Number of commodities used to compute pct_change_harga_pangan. |  |
| nama_kota | text | BPS IHK city name. | not_null_mart_inflasi_vs_harga_nama_kota |
| nama_provinsi | character varying(64) | Province name. |  |
| pct_change_harga_pangan | numeric | Average MoM change (%) in the province x commodity median price vs. the previous calendar month (fct_harga_bulanan); NULL if that month's or the previous month's price is missing. |  |
