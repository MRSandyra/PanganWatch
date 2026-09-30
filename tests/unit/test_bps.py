"""Offline tests for the BPS parser/client (F3b). Fixture = trimmed real BPS responses."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from panganwatch.sources import bps

FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "bps_ihk_sample.json").read_text(encoding="utf-8")
)
KEY = "some-secret-value"


def test_api_key_status_empty(monkeypatch):
    monkeypatch.delenv("BPS_API_KEY", raising=False)
    assert bps.api_key_status() == "EMPTY"


def test_api_key_status_set(monkeypatch):
    monkeypatch.setenv("BPS_API_KEY", KEY)
    assert bps.api_key_status() == "SET"


def test_main_run_skips_cleanly_when_key_missing(monkeypatch):
    monkeypatch.delenv("BPS_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(
        bps, "skip_run", lambda run_id, source, reason: calls.append((source, reason))
    )

    exit_code = bps.main(["--run"])

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0][0] == "BPS"
    assert KEY not in calls[0][1]


def test_parse_data_ihk_reads_months_only():
    cells = bps.parse_data(FIXTURE["2245_125"], bps.VAR_IHK)
    assert len(cells) == 48  # 4 vervar x 12 months, the annual column is not read
    banda_jan = next(c for c in cells if c["kode_vervar"] == 4 and c["bulan"] == date(2025, 1, 1))
    assert banda_jan["nama_kota"] == "KOTA BANDA ACEH"
    assert banda_jan["value"] == 105.91


def test_parse_data_skips_absent_cells():
    payload = json.loads(json.dumps(FIXTURE["2245_125"]))
    del payload["datacontent"]["42245012512"]  # Dec 2025 for vervar 4
    cells = bps.parse_data(payload, bps.VAR_IHK)
    assert len(cells) == 47
    assert not any(c["kode_vervar"] == 4 and c["bulan"] == date(2025, 12, 1) for c in cells)


def test_compute_records_mtm_yoy_and_national_skip():
    ihk = bps.parse_data(FIXTURE["2245_124"], bps.VAR_IHK) + bps.parse_data(
        FIXTURE["2245_125"], bps.VAR_IHK
    )
    yoy = bps.parse_data(FIXTURE["2249_125"], bps.VAR_YOY)
    records, quarantined, national = bps.compute_records(ihk, yoy, "run-1")

    assert national == 24  # INDONESIA x 24 months is an aggregate, not a city
    assert quarantined == []
    assert {r["nama_kota"] for r in records} == {"KAB ACEH TENGAH", "KOTA BANDA ACEH", "KOTA MEDAN"}
    banda = {r["bulan"]: r for r in records if r["kode_vervar"] == 4}
    # M-to-M across the year boundary, derived from consecutive IHK values
    assert banda[date(2025, 1, 1)]["ihk"] == 105.91
    assert banda[date(2025, 1, 1)]["inflasi_mtm"] == round((105.91 / 106.41 - 1) * 100, 2)
    assert banda[date(2025, 1, 1)]["inflasi_yoy"] == 1.12
    # first month of the series has no previous month -> NULL, never 0
    assert banda[date(2024, 1, 1)]["inflasi_mtm"] is None
    assert all(r["run_id"] == "run-1" and r["source"] == "BPS" for r in records)


def test_compute_records_gap_month_gives_null_mtm():
    cells = [c for c in bps.parse_data(FIXTURE["2245_125"], bps.VAR_IHK) if c["kode_vervar"] == 4]
    cells = [c for c in cells if c["bulan"].month != 3]  # March missing
    records, _, _ = bps.compute_records(cells, [], "r")
    by_month = {r["bulan"].month: r for r in records}
    assert by_month[4]["inflasi_mtm"] is None  # previous calendar month absent, not LAG-ed
    assert by_month[2]["inflasi_mtm"] is not None


def test_compute_records_quarantines_non_numeric_ihk():
    cells = [
        {"kode_vervar": 4, "nama_kota": "KOTA BANDA ACEH", "bulan": date(2025, 1, 1), "value": "-"},
        {
            "kode_vervar": 4,
            "nama_kota": "KOTA BANDA ACEH",
            "bulan": date(2025, 2, 1),
            "value": 100.0,
        },
    ]
    records, quarantined, _ = bps.compute_records(cells, [], "r")
    assert len(records) == 1 and len(quarantined) == 1


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _resp(status, body):
    return httpx.Response(status, json=body, request=httpx.Request("GET", "https://x"))


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(bps.time, "sleep", lambda s: None)


def test_fetch_json_stops_on_429_without_retry():
    client = _Client([_resp(429, {"status": "Error"})])
    with pytest.raises(bps.BPSRateLimitError):
        bps.fetch_json("list/x", KEY, client)
    assert client.calls == 1


def test_fetch_json_retries_5xx_then_succeeds():
    client = _Client([_resp(503, {}), _resp(200, {"status": "OK", "data": []})])
    body, status = bps.fetch_json("list/x", KEY, client)
    assert status == 200 and body["status"] == "OK" and client.calls == 2


def test_fetch_json_error_status_never_leaks_key():
    client = _Client([_resp(200, {"status": "Error", "message": f"invalid key {KEY}"})])
    with pytest.raises(bps.BPSError) as exc:
        bps.fetch_json("list/x", KEY, client)
    assert KEY not in str(exc.value)


def test_fetch_json_transport_error_never_leaks_key():
    err = httpx.ConnectError(f"boom https://webapi/key/{KEY}/")
    client = _Client([err] * bps.MAX_RETRIES)
    with pytest.raises(bps.BPSError) as exc:
        bps.fetch_json("list/x", KEY, client)
    assert KEY not in str(exc.value) and client.calls == bps.MAX_RETRIES


def test_fetch_data_detects_variable_id_drift(monkeypatch):
    drifted = json.loads(json.dumps(FIXTURE["2245_125"]))
    drifted["var"][0]["label"] = "Something else entirely"
    monkeypatch.setattr(bps, "fetch_json", lambda path, key, client=None: (drifted, 200))
    with pytest.raises(bps.BPSError, match="drifted"):
        bps.fetch_data(bps.VAR_IHK, 125, KEY)
