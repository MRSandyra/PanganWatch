from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from panganwatch.sources import hdx_wfp

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "wfp_food_prices_sample.csv"

PROVINCE_MAP = {"ACEH": "11", "DKI JAKARTA": "31", "JAWA BARAT": "32"}
COMMODITY_MAP = {
    "Rice (medium quality)": "0101",
    "Onions (shallot, medium)": "0104",
    "Chili (bird's eye)": "0102",
    "Sugar (local)": "0109",
}


def load_fixture_rows() -> list[dict[str, str]]:
    with FIXTURE.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_normalize_strips_punctuation_and_case():
    assert hdx_wfp.normalize("Daerah Istimewa Yogyakarta") == "daerah istimewa yogyakarta"
    assert hdx_wfp.normalize("  DKI   Jakarta! ") == "dki jakarta"


def test_find_date_range_reads_actual_min_max():
    min_d, max_d = hdx_wfp.find_date_range(FIXTURE)
    assert min_d == date(2007, 1, 15)
    assert max_d == date(2026, 6, 15)


def test_parse_and_map_row_maps_known_province_and_commodity():
    rows = load_fixture_rows()
    row = next(
        r for r in rows if r["admin1"] == "ACEH" and r["commodity"] == "Rice (medium quality)"
    )

    record, reason = hdx_wfp.parse_and_map_row(row, PROVINCE_MAP, COMMODITY_MAP)

    assert reason is None
    assert record["kode_provinsi_bps"] == "11"
    assert record["komoditas_id"] == "0101"
    assert record["source"] == "HDX WFP"
    assert record["harga"] > 0


def test_parse_and_map_row_quarantines_unmapped_province():
    rows = load_fixture_rows()
    row = next(r for r in rows if r["admin1"] == "")

    record, reason = hdx_wfp.parse_and_map_row(row, PROVINCE_MAP, COMMODITY_MAP)

    assert record is None
    assert "province not mapped" in reason


def test_parse_and_map_row_quarantines_unmapped_commodity():
    row = {
        "date": "2026-06-15",
        "admin1": "ACEH",
        "commodity": "Fuel (kerosene)",
        "price": "2874",
        "market": "Pasar X",
        "unit": "L",
    }

    record, reason = hdx_wfp.parse_and_map_row(row, PROVINCE_MAP, COMMODITY_MAP)

    assert record is None
    assert "commodity not mapped" in reason


def test_parse_and_map_row_falls_back_to_normalized_province_match():
    row = {
        "date": "2026-06-15",
        "admin1": "aceh",
        "commodity": "Rice (medium quality)",
        "price": "15000",
        "market": "Pasar X",
        "unit": "KG",
    }

    record, reason = hdx_wfp.parse_and_map_row(row, PROVINCE_MAP, COMMODITY_MAP)

    assert reason is None
    assert record["kode_provinsi_bps"] == "11"


def test_parse_and_map_row_rejects_non_positive_price():
    row = {
        "admin1": "ACEH",
        "commodity": "Rice (medium quality)",
        "price": "0",
        "market": "Pasar X",
        "unit": "KG",
    }

    record, reason = hdx_wfp.parse_and_map_row(row, PROVINCE_MAP, COMMODITY_MAP)

    assert record is None
    assert "non-positive price" in reason


def test_run_ingestion_window_filters_out_old_rows(monkeypatch):
    """Rows outside [start_date, end_date] must not be counted, even before mapping."""
    monkeypatch.setattr(hdx_wfp, "load_province_mapping", lambda: PROVINCE_MAP)
    monkeypatch.setattr(hdx_wfp, "load_commodity_mapping", lambda: COMMODITY_MAP)

    monkeypatch.setattr(
        hdx_wfp, "get_postgres_connection", lambda: SimpleNamespace(close=lambda: None)
    )
    stored = []
    monkeypatch.setattr(hdx_wfp, "store_raw", lambda **kwargs: stored.append(kwargs))
    upserted = []
    monkeypatch.setattr(
        hdx_wfp, "upsert_harga_pangan", lambda record, conn=None: upserted.append(record)
    )
    quarantined = []
    monkeypatch.setattr(
        hdx_wfp,
        "append_unmapped",
        lambda run_id, dataset, record, reason: quarantined.append(reason),
    )

    rows_fetched, rows_loaded, rows_quarantined = hdx_wfp.run_ingestion(
        FIXTURE, date(2026, 1, 1), date(2026, 12, 31), "test-run"
    )

    # Only 2026-06-15 rows (aceh_rice x2, jakarta_onion x2) are inside the window.
    assert rows_fetched == 4
    assert rows_loaded == 4
    assert rows_quarantined == 0
    assert len(upserted) == 4
    assert len(stored) == 1  # one monthly bronze chunk (2026-06)
