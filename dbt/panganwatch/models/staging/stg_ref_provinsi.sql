{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    kode_bps,
    kode_kemendagri,
    nama_provinsi,
    ibu_kota,
    lat,
    lon,
    source
FROM ref.ref_provinsi