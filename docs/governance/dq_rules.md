# Data Quality Rules

Generated from `config/dq_rules.yml`. Do not edit manually — run `make dq-docs`.
Total rules: 27

| rule_id | dataset | column | type | dimension | severity | owner | description |
|---------|---------|--------|------|-----------|----------|-------|-------------|
| HP-001 | silver.harga_pangan | tanggal | not_null | completeness | error | data-steward | Date is required for every food-price record |
| HP-002 | silver.harga_pangan | kode_provinsi_bps | not_null | completeness | error | data-steward | BPS province code is required |
| HP-003 | silver.harga_pangan | komoditas_id | not_null | completeness | error | data-steward | Commodity ID is required |
| HP-004 | silver.harga_pangan | harga | not_null | completeness | error | data-steward | Price is required |
| HP-005 | silver.harga_pangan | harga | range | validity | error | data-steward | Price must be > 0 and < 1,000,000 per unit |
| HP-006 | silver.harga_pangan | kode_provinsi_bps | in_reference | consistency | error | data-steward | BPS province code must exist in ref.ref_provinsi |
| HP-007 | silver.harga_pangan | komoditas_id | in_reference | consistency | error | data-steward | Commodity ID must exist in ref.ref_komoditas |
| HP-008 | silver.harga_pangan | natural_key | unique_key | uniqueness | error | data-steward | The natural key must be unique (duplicate check via upsert) |
| HP-009 | silver.harga_pangan | tanggal | range | validity | error | data-steward | Date must not be in the future (Asia/Jakarta timezone) |
| HP-010 | silver.harga_pangan | harga | max_pct_change | accuracy | warn | data-steward | Month-over-month price change for the same key <= 100% (HDX WFP data is monthly grain) |
| HP-011 | silver.harga_pangan | tanggal | freshness | timeliness | warn | data-steward | Latest date <= 45 days ago (HDX WFP is MONTHLY-grain, not daily -- DEC-033; 45 days = ~1.5 monthly cycles, lenient toward the source's publication delay) |
| HP-012 | silver.harga_pangan | completeness_ratio | completeness_ratio | completeness | warn | data-steward | Per date, >= 80% of the 38 provinces have data for the main commodities that ARE present in HDX WFP (beras 0101, bawang merah 0104; chili is absent from the 2025-06..2026-06 data window) -- the old filter used a fake id so it passed vacuously (DEC-036) |
| HP-014 | silver.harga_pangan | kode_provinsi_bps | completeness_ratio | completeness | warn | data-steward | Province coverage: per date, all 38 provinces have price data. Actual 34/38 (89.5%): Papua Selatan, Papua Tengah, Papua Pegunungan, Papua Barat Daya never appear in HDX WFP -- a real data-quality finding, deliberately failing (warn), see incident_log.md (DEC-036) |
| CH-001 | silver.cuaca_harian | tanggal | not_null | completeness | error | data-steward | Date is required for daily weather |
| CH-002 | silver.cuaca_harian | kode_provinsi_bps | not_null | completeness | error | data-steward | BPS province code is required for weather |
| CH-003 | silver.cuaca_harian | precipitation_mm | not_null | completeness | error | data-steward | Rainfall is required |
| CH-004 | silver.cuaca_harian | precipitation_mm | range | validity | error | data-steward | Rainfall must be 0-500 mm/day |
| CH-005 | silver.cuaca_harian | tmin_c | range | accuracy | error | data-steward | Minimum temperature must be -10 to 50 C |
| CH-006 | silver.cuaca_harian | tmax_c | range | accuracy | error | data-steward | Maximum temperature must be -10 to 50 C |
| CH-007 | silver.cuaca_harian | tmin_c | custom_range | accuracy | error | data-steward | Minimum temperature must be <= maximum temperature |
| CH-008 | silver.cuaca_harian | natural_key | unique_key | uniqueness | error | data-steward | The (tanggal, kode_provinsi_bps) key must be unique |
| CT-001 | silver.cuaca_terkini | observed_at | freshness | timeliness | warn | data-steward | Latest observed_at <= 2x the polling interval |
| IN-001 | silver.inflasi_kota | inflasi_mtm | range | validity | warn | data-steward | Month-over-month inflation (derived from the BPS IHK) between -20% and 50%; NULL is allowed in the first month of a series (it cannot be derived) |
| RF-001 | ref.ref_provinsi | row_count | row_count | completeness | error | data-steward | There must be exactly 38 province rows |
| RF-002 | ref.ref_provinsi | lat | range | validity | error | data-steward | Province latitude must be within Indonesia's bounds |
| RF-003 | ref.ref_provinsi | lon | range | validity | error | data-steward | Province longitude must be within Indonesia's bounds |
| HP-013 | silver.harga_pangan | cross_source_diff | cross_source_diff | consistency | warn | data-steward | Difference in the national median across sources <= 15% (N/A with a single source) |

## Summary by DAMA Dimension

| Dimension | Count |
|-----------|-------|
| completeness | 10 |
| validity | 6 |
| accuracy | 4 |
| consistency | 3 |
| timeliness | 2 |
| uniqueness | 2 |

## Summary by Severity

| Severity | Count |
|----------|-------|
| error | 20 |
| warn | 7 |