{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- Grain is "month" (not "week" per Appendix B) because the price source is
-- monthly-grain (DEC-010): a weekly aggregation is meaningless for data that
-- only has one observation per month.
WITH bulanan AS (
    SELECT
        date_trunc('month', tanggal)::date AS bulan,
        kode_provinsi_bps,
        komoditas_id,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY harga_median) AS harga_median_provinsi
    FROM {{ ref('fct_harga_bulanan') }}
    GROUP BY 1, 2, 3
),
nasional AS (
    SELECT
        bulan,
        komoditas_id,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY harga_median_provinsi) AS harga_median_nasional
    FROM bulanan
    GROUP BY 1, 2
)
SELECT
    b.bulan,
    b.kode_provinsi_bps,
    b.komoditas_id,
    b.harga_median_provinsi,
    n.harga_median_nasional,
    ROUND(
        (((b.harga_median_provinsi - n.harga_median_nasional) / NULLIF(n.harga_median_nasional, 0)) * 100)::numeric,
        2
    ) AS pct_deviasi,
    RANK() OVER (
        PARTITION BY b.bulan, b.komoditas_id
        ORDER BY ABS(b.harga_median_provinsi - n.harga_median_nasional) DESC
    ) AS rank_deviasi
FROM bulanan b
JOIN nasional n ON b.bulan = n.bulan AND b.komoditas_id = n.komoditas_id
