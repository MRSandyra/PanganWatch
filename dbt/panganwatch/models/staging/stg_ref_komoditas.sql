{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    komoditas_id,
    nama_kanonis,
    kelompok,
    satuan,
    het
FROM ref.ref_komoditas