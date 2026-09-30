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
    kode_kabkota_bps,
    komoditas_id,
    jenis_pasar,
    harga,
    satuan,
    source,
    run_id,
    loaded_at
FROM {{ source('silver', 'harga_pangan') }}
