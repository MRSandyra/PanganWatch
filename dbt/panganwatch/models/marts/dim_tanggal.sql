{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- Range = the union of the price + weather data ranges (Appendix B).
{% set start_expr %}
    (SELECT MIN(d) FROM (
        SELECT MIN(tanggal) AS d FROM {{ ref('stg_harga_pangan') }}
        UNION ALL
        SELECT MIN(tanggal) FROM {{ ref('stg_cuaca_harian') }}
    ) bounds_min)
{% endset %}
{% set end_expr %}
    (SELECT MAX(d) + INTERVAL '1 day' FROM (
        SELECT MAX(tanggal) AS d FROM {{ ref('stg_harga_pangan') }}
        UNION ALL
        SELECT MAX(tanggal) FROM {{ ref('stg_cuaca_harian') }}
    ) bounds_max)
{% endset %}

WITH spine AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date=start_expr,
        end_date=end_expr
    ) }}
)
SELECT
    date_day::date AS tanggal,
    TO_CHAR(date_day, 'IYYY-"W"IW') AS minggu_iso,
    (date_day - (EXTRACT(ISODOW FROM date_day)::int - 1) * INTERVAL '1 day')::date AS awal_minggu,
    EXTRACT(MONTH FROM date_day)::int AS bulan,
    EXTRACT(YEAR FROM date_day)::int AS tahun,
    EXTRACT(ISODOW FROM date_day) IN (6, 7) AS is_weekend
FROM spine
