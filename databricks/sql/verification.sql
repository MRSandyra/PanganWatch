-- Execute only against a completed cloud snapshot; record output in docs/migration/evidence.
SELECT 'harga_pangan' AS dataset, COUNT(*) AS rows, COUNT(DISTINCT concat_ws('|', tanggal, kode_provinsi_bps, coalesce(kode_kabkota_bps, ''), komoditas_id, jenis_pasar, source)) AS keys
FROM ${PANGANWATCH_CATALOG}.pw_silver.harga_pangan;
SELECT rule_id, severity, rows_checked, rows_failed, pass_rate
FROM ${PANGANWATCH_CATALOG}.pw_governance.dq_results
ORDER BY checked_at DESC, rule_id;
