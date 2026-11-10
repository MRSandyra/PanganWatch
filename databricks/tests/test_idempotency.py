from src.silver import KEYS


def test_silver_business_keys_preserve_local_upsert_contracts():
    assert KEYS["harga_pangan"][:3] == ["tanggal", "kode_provinsi_bps", "kode_kabkota_bps"]
    assert KEYS["cuaca_harian"] == ["tanggal", "kode_provinsi_bps"]
    assert KEYS["inflasi_kota"] == ["bulan", "kode_vervar"]
