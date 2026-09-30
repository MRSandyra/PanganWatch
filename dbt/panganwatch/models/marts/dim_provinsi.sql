{{
    config(
        materialized='table',
        schema='gold'
    )
}}

SELECT
    kode_bps AS kode_provinsi_bps,
    nama_provinsi,
    ibu_kota,
    lat,
    lon,
    kode_kemendagri
FROM {{ ref('stg_ref_provinsi') }}
