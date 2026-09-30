{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    id,
    tanggal,
    kode_provinsi_bps,
    precipitation_mm,
    tmax_c,
    tmin_c,
    source,
    run_id,
    loaded_at
FROM {{ source('silver', 'cuaca_harian') }}
