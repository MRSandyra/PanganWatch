{{
    config(
        materialized='table',
        schema='gold'
    )
}}

SELECT
    komoditas_id,
    nama_kanonis,
    kelompok,
    satuan,
    het
FROM {{ ref('stg_ref_komoditas') }}
