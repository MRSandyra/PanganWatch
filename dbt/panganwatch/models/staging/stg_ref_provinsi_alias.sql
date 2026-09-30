{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    nama_sumber,
    sumber,
    kode_bps,
    match_method,
    alasan
FROM ref.ref_provinsi_alias