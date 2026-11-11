from src.reconciliation import COMPARISON_COLUMNS, reconcile_records


def test_reconciliation_reports_field_difference():
    findings = reconcile_records(
        [{"tanggal": "2026-01-15", "kode": "11", "harga": "100.00"}],
        [{"tanggal": "2026-01-15", "kode": "11", "harga": "101.00"}],
        ["tanggal", "kode"],
    )
    assert findings[0]["field"] == "harga"
    assert findings[0]["classification"] == "VALUE_MISMATCH"


def test_reconciliation_reports_missing_key():
    findings = reconcile_records([{"id": "a"}], [{"id": "b"}], ["id"])
    assert len(findings) == 2
    assert {item["classification"] for item in findings} == {"MISSING_KEY"}


def test_source_replay_compares_contract_fields_not_run_audit_columns():
    assert "run_id" not in COMPARISON_COLUMNS["harga_pangan"]
    assert "loaded_at" not in COMPARISON_COLUMNS["cuaca_harian"]
    assert "harga" in COMPARISON_COLUMNS["harga_pangan"]
    assert "precipitation_mm" in COMPARISON_COLUMNS["cuaca_harian"]
