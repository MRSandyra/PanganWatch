{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- Appendix B: month x city. Inflation (BPS IHK) per IHK city is paired with
-- the food-price change in that city's province. The grains differ (IHK per
-- city, HDX WFP prices per province), hence the city -> province mapping via
-- ref_ihk_kota.
-- pct_change_harga_pangan = the average MoM change in the province x
-- commodity median price vs. the PREVIOUS CALENDAR MONTH (a month-1 join, not
-- LAG: some months are missing from the source, e.g. January 2026, and LAG
-- would then measure a 2-month gap as "MoM"). NULL if that month's or the
-- previous month's price is missing.
WITH harga_komoditas AS (
    SELECT
        date_trunc('month', tanggal)::date AS bulan,
        kode_provinsi_bps,
        komoditas_id,
        AVG(harga_median) AS harga
    FROM {{ ref('fct_harga_bulanan') }}
    GROUP BY 1, 2, 3
),
harga_mom AS (
    SELECT
        c.bulan,
        c.kode_provinsi_bps,
        100.0 * (c.harga - p.harga) / NULLIF(p.harga, 0) AS pct
    FROM harga_komoditas c
    JOIN harga_komoditas p
        ON p.kode_provinsi_bps = c.kode_provinsi_bps
        AND p.komoditas_id = c.komoditas_id
        AND p.bulan = (c.bulan - INTERVAL '1 month')::date
),
pangan_provinsi AS (
    SELECT
        bulan,
        kode_provinsi_bps,
        ROUND(AVG(pct)::numeric, 2) AS pct_change_harga_pangan,
        COUNT(*) AS n_komoditas
    FROM harga_mom
    GROUP BY 1, 2
)
SELECT
    i.bulan,
    i.kode_vervar,
    i.nama_kota,
    i.kode_provinsi_bps,
    p.nama_provinsi,
    i.ihk,
    i.inflasi_mtm,
    i.inflasi_yoy,
    h.pct_change_harga_pangan,
    h.n_komoditas
FROM {{ ref('stg_inflasi_kota') }} i
LEFT JOIN {{ ref('dim_provinsi') }} p ON i.kode_provinsi_bps = p.kode_provinsi_bps
LEFT JOIN pangan_provinsi h
    ON i.kode_provinsi_bps = h.kode_provinsi_bps AND i.bulan = h.bulan
