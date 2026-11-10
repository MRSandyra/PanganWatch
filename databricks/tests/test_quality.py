from pathlib import Path

import yaml

from src.quality import has_error_failures, mapped_rule_ids


def test_every_existing_dq_rule_has_a_migration_mapping():
    root = Path(__file__).resolve().parents[2]
    original = yaml.safe_load((root / "config" / "dq_rules.yml").read_text(encoding="utf-8"))
    assert {item["rule_id"] for item in original["rules"]} == mapped_rule_ids()


def test_only_error_failures_block_gold():
    assert not has_error_failures([{"severity": "warn", "rows_failed": 10}])
    assert has_error_failures([{"severity": "error", "rows_failed": 1}])
