{{
    config(
        materialized='incremental',
        unique_key=['tanggal', 'kode_provinsi_bps', 'komoditas_id', 'jenis_pasar', 'source'],
        schema='gold'
    )
}}

-- Named "fct_harga_bulanan" (not "fct_harga_harian" per Appendix B) because
-- the price source (HDX WFP) is monthly-grain: one snapshot on the 15th of
-- each month (DEC-010). This table's grain is still "per date" as-is (no
-- forced explicit month aggregation), but the only `tanggal` values present
-- are those monthly snapshot dates themselves.
-- Kab/kota is aggregated to province by median: kode_kabkota_bps in
-- silver.harga_pangan (the HDX source) is always NULL, so the aggregation
-- below is already at the province level.
WITH base AS (
    SELECT
        tanggal,
        kode_provinsi_bps,
        komoditas_id,
        jenis_pasar,
        source,
        harga
    FROM {{ ref('stg_harga_pangan') }}
    {% if is_incremental() %}
    WHERE tanggal > (SELECT MAX(tanggal) FROM {{ this }})
    {% endif %}
)
SELECT
    tanggal,
    kode_provinsi_bps,
    komoditas_id,
    jenis_pasar,
    source,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY harga) AS harga_median,
    MIN(harga) AS harga_min,
    MAX(harga) AS harga_max,
    COUNT(*) AS n_observasi,
    -- Placeholder: the F4 rule engine does not yet write a per-row dq_warn
    -- flag on silver rows, so this column is always 0 for now (not a
    -- fabricated number; F4 needs to be extended to fill this in for real).
    0 AS n_dq_warn
FROM base
GROUP BY tanggal, kode_provinsi_bps, komoditas_id, jenis_pasar, source
