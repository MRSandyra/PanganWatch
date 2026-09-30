{{ config(severity='warn') }}

-- BPS IHK cities not mapped to a province via ref_ihk_kota. Rows returned by
-- this test are cities that need to be added to scripts/build_ref_ihk_kota.py;
-- reported as WARN, not silently ignored (docs/governance/ihk_mapping_report.md).
SELECT DISTINCT kode_vervar, nama_kota
FROM {{ ref('stg_inflasi_kota') }}
WHERE kode_provinsi_bps IS NULL
