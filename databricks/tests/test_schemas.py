from src.schemas import SCHEMA_SPECS


def test_explicit_contracts_match_core_silver_datasets():
    assert set(SCHEMA_SPECS) == {"harga_pangan", "cuaca_harian", "inflasi_kota"}
    assert "harga" in {field[0] for field in SCHEMA_SPECS["harga_pangan"]}
    assert "tmin_c" in {field[0] for field in SCHEMA_SPECS["cuaca_harian"]}
