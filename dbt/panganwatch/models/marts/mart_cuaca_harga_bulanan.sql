{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- Named "mart_cuaca_harga_bulanan" (not "..._mingguan" per Appendix B) because
-- the price grain is monthly (DEC-010); the chili/shallot-vs-rain lag is still
-- computed in Python (F9), using daily silver.cuaca_harian data directly.
-- The "heavy rain day" threshold = 50mm/day, from config/settings.yaml
-- weather.rain_intensity.sedang_max (the starting point of BMKG's "heavy" category, DEC-013).
WITH cuaca_bulanan AS (
    SELECT
        date_trunc('month', tanggal)::date AS bulan,
        kode_provinsi_bps,
        SUM(CASE WHEN precipitation_mm >= 50 THEN 1 ELSE 0 END) AS hari_hujan_lebat,
        SUM(precipitation_mm) AS total_hujan_mm
    FROM {{ ref('stg_cuaca_harian') }}
    GROUP BY 1, 2
),
harga_bulanan AS (
    SELECT
        date_trunc('month', f.tanggal)::date AS bulan,
        f.kode_provinsi_bps,
        k.kelompok,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.harga_median) AS harga_median
    FROM {{ ref('fct_harga_bulanan') }} f
    JOIN {{ ref('dim_komoditas') }} k ON f.komoditas_id = k.komoditas_id
    GROUP BY 1, 2, 3
),
joined AS (
    SELECT
        h.bulan,
        h.kode_provinsi_bps,
        h.kelompok,
        h.harga_median,
        c.hari_hujan_lebat,
        c.total_hujan_mm
    FROM harga_bulanan h
    LEFT JOIN cuaca_bulanan c
        ON h.bulan = c.bulan AND h.kode_provinsi_bps = c.kode_provinsi_bps
)
SELECT
    bulan,
    kode_provinsi_bps,
    kelompok,
    harga_median,
    hari_hujan_lebat,
    total_hujan_mm,
    ROUND(
        (100.0 * (harga_median - LAG(harga_median) OVER (PARTITION BY kode_provinsi_bps, kelompok ORDER BY bulan))
        / NULLIF(LAG(harga_median) OVER (PARTITION BY kode_provinsi_bps, kelompok ORDER BY bulan), 0))::numeric,
        2
    ) AS pct_change_mom
FROM joined
