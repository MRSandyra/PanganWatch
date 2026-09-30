{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- F3b (DEC-039/DEC-040): silver.inflasi_kota per BPS IHK city + the city ->
-- kab/kota -> province mapping via the ref_ihk_kota seed (built from
-- ref_kabkota by scripts/build_ref_ihk_kota.py), not ad hoc name matching.
-- Cities without a mapping still appear, with kode_provinsi_bps NULL, and are
-- reported by the assert_ihk_kota_all_mapped test.
SELECT
    s.bulan,
    s.kode_vervar,
    s.nama_kota,
    m.kode_kabkota_bps,
    m.kode_provinsi_bps,
    m.match_method,
    s.ihk,
    s.inflasi_mtm,
    s.inflasi_yoy,
    s.run_id,
    s.loaded_at
FROM {{ source('silver', 'inflasi_kota') }} s
LEFT JOIN {{ ref('ref_ihk_kota') }} m ON s.kode_vervar = m.kode_vervar
