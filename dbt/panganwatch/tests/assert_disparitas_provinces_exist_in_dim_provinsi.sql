-- Singular test: every province in mart_disparitas_provinsi must exist in dim_provinsi.
-- Passes if this query returns 0 rows.
SELECT d.kode_provinsi_bps
FROM {{ ref('mart_disparitas_provinsi') }} d
LEFT JOIN {{ ref('dim_provinsi') }} p ON d.kode_provinsi_bps = p.kode_provinsi_bps
WHERE p.kode_provinsi_bps IS NULL
