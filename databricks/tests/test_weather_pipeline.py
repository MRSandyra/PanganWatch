from pathlib import Path

from src.weather import transform_open_meteo_daily


def test_weather_transform_is_importable_without_pyspark():
    assert callable(transform_open_meteo_daily)


def test_weather_snapshot_script_uses_committed_province_seed_and_era5():
    source = (Path(__file__).resolve().parents[2] / "scripts" / "fetch_open_meteo_snapshot.py").read_text(
        encoding="utf-8"
    )
    assert "ref_provinsi.csv" in source
    assert '"models": "era5"' in source
    assert "locations-per-request" in source
    assert "Retry-After" in source
    assert ".partial" in source
