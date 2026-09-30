from __future__ import annotations

from panganwatch.sources import open_meteo

PROVINCE = {
    "kode_bps": "31",
    "nama_provinsi": "Daerah Khusus Ibukota Jakarta",
    "lat": -6.2,
    "lon": 106.8,
}


def test_to_daily_records_maps_all_fields():
    daily_response = {
        "daily": {
            "time": ["2026-06-01", "2026-06-02"],
            "precipitation_sum": [1.6, 55.0],
            "temperature_2m_max": [33.2, 30.5],
            "temperature_2m_min": [26.0, 25.6],
        }
    }

    records = open_meteo.to_daily_records(PROVINCE, daily_response, "Open-Meteo Archive")

    assert len(records) == 2
    assert records[0] == {
        "tanggal": "2026-06-01",
        "kode_provinsi_bps": "31",
        "precipitation_mm": 1.6,
        "tmax_c": 33.2,
        "tmin_c": 26.0,
        "source": "Open-Meteo Archive",
    }
    assert records[1]["precipitation_mm"] == 55.0


def test_to_daily_records_handles_missing_daily_block():
    records = open_meteo.to_daily_records(PROVINCE, {}, "Open-Meteo Archive")
    assert records == []


def test_run_ingestion_strips_volatile_generationtime_before_storing(monkeypatch):
    """generationtime_ms varies on every API call and must not leak into the
    bronze payload, or re-running the same window would never be idempotent
    (different hash each time)."""
    from types import SimpleNamespace

    provinces = [PROVINCE]
    monkeypatch.setattr(open_meteo, "load_provinces", lambda: provinces)
    monkeypatch.setattr(
        open_meteo, "get_postgres_connection", lambda: SimpleNamespace(close=lambda: None)
    )
    monkeypatch.setattr(open_meteo, "upsert_cuaca_harian", lambda record, conn=None: None)

    responses = [
        {
            "generationtime_ms": 12.34,
            "daily": {
                "time": [],
                "precipitation_sum": [],
                "temperature_2m_max": [],
                "temperature_2m_min": [],
            },
        }
    ]
    monkeypatch.setattr(open_meteo, "fetch_archive", lambda batch, s, e: responses)

    stored = []
    monkeypatch.setattr(open_meteo, "store_raw", lambda **kwargs: stored.append(kwargs))

    import datetime

    open_meteo.run_ingestion(datetime.date(2026, 6, 1), datetime.date(2026, 6, 1), "test-run")

    assert "generationtime_ms" not in stored[0]["payload"][0]


def test_run_ingestion_batches_and_upserts(monkeypatch):
    from types import SimpleNamespace

    provinces = [PROVINCE, {"kode_bps": "11", "nama_provinsi": "Aceh", "lat": 5.5, "lon": 95.3}]
    monkeypatch.setattr(open_meteo, "load_provinces", lambda: provinces)
    monkeypatch.setattr(open_meteo, "MAX_LOCATIONS_PER_REQUEST", 38)
    monkeypatch.setattr(
        open_meteo, "get_postgres_connection", lambda: SimpleNamespace(close=lambda: None)
    )

    fake_daily = {
        "daily": {
            "time": ["2026-06-01"],
            "precipitation_sum": [10.0],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [24.0],
        }
    }
    monkeypatch.setattr(
        open_meteo, "fetch_archive", lambda batch, s, e: [fake_daily for _ in batch]
    )

    stored = []
    monkeypatch.setattr(open_meteo, "store_raw", lambda **kwargs: stored.append(kwargs))
    upserted = []
    monkeypatch.setattr(
        open_meteo, "upsert_cuaca_harian", lambda record, conn=None: upserted.append(record)
    )

    import datetime

    rows_fetched, rows_loaded, rows_quarantined = open_meteo.run_ingestion(
        datetime.date(2026, 6, 1), datetime.date(2026, 6, 1), "test-run"
    )

    assert rows_fetched == 2
    assert rows_loaded == 2
    assert rows_quarantined == 0
    assert len(stored) == 1
    assert len(upserted) == 2
