from pathlib import Path

import yaml
from src.quality import cuaca_harian_rules, harga_pangan_rules, has_error_failures, mapped_rule_ids


def test_every_existing_dq_rule_has_a_migration_mapping():
    root = Path(__file__).resolve().parents[2]
    original = yaml.safe_load((root / "config" / "dq_rules.yml").read_text(encoding="utf-8"))
    assert {item["rule_id"] for item in original["rules"]} == mapped_rule_ids()


def test_only_error_failures_block_gold():
    assert not has_error_failures([{"severity": "warn", "rows_failed": 10}])
    assert has_error_failures([{"severity": "error", "rows_failed": 1}])


def test_hdx_wfp_quality_scope_contains_the_expected_price_rules():
    rule_ids = {rule["rule_id"] for rule in harga_pangan_rules()}
    assert {"HP-001", "HP-008", "HP-014"}.issubset(rule_ids)
    assert "CH-001" not in rule_ids


def test_weather_quality_scope_contains_only_daily_weather_rules():
    rule_ids = {rule["rule_id"] for rule in cuaca_harian_rules()}
    assert {"CH-001", "CH-007", "CH-008"}.issubset(rule_ids)
    assert "CT-001" not in rule_ids
