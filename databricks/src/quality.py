"""Spark equivalent of the existing post-load DQ semantics; no silent row loss."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def mapped_rule_ids(path: Path | None = None) -> set[str]:
    value = yaml.safe_load(
        (path or ROOT / "config" / "quality_mapping.yml").read_text(encoding="utf-8")
    )
    return set(value["rules"])


def evaluate_rule(frame, rule: dict):
    """Return only failed rows for local/Databricks rule evaluation. Coverage stays warning-only."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    kind, column, params = rule["type"], rule["column"], rule.get("params", {})
    if kind == "not_null":
        return frame.where(sf.col(column).isNull())
    if kind == "range":
        lower, upper = params.get("min"), params.get("max")
        condition = sf.lit(False)
        if lower is not None:
            condition = condition | (sf.col(column) < sf.lit(lower))
        if upper is not None:
            condition = condition | (sf.col(column) > sf.lit(upper))
        return (
            frame.where(sf.col(column).isNull() | condition)
            if not params.get("allow_null", False)
            else frame.where(condition)
        )
    if kind == "custom_range":
        other = params["other_column"]
        return frame.where(
            sf.col(column).isNotNull()
            & sf.col(other).isNotNull()
            & (sf.col(column) > sf.col(other))
        )
    if kind == "unique_key":
        keys = params.get("key_columns", [])
        return frame.join(
            frame.groupBy(*keys).count().where("count > 1").select(*keys), keys, "inner"
        )
    return frame.limit(0)  # aggregate/freshness rules are evaluated by their calling notebook.


def has_error_failures(results: list[dict]) -> bool:
    return any(item["severity"] == "error" and item["rows_failed"] > 0 for item in results)
