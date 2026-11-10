"""Spark equivalent of the existing post-load DQ semantics; no silent row loss."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import MigrationConfig

# `quality.py` lives at <project>/databricks/src/quality.py.
ROOT = Path(__file__).resolve().parents[1]
SOURCE_RULES = ROOT.parent / "config" / "dq_rules.yml"


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


def harga_pangan_rules(path: Path | None = None) -> list[dict]:
    """Load only the DQ rules applicable to the migrated HDX/WFP Silver table."""
    value = yaml.safe_load((path or SOURCE_RULES).read_text(encoding="utf-8"))
    return [rule for rule in value["rules"] if rule["dataset"] == "silver.harga_pangan"]


def _rule_result(rule: dict, run_id: str, rows_checked: int, rows_failed: int | None, status: str, note: str):
    return {
        "run_id": run_id,
        "rule_id": rule["rule_id"],
        "dataset": rule["dataset"],
        "column_name": rule["column"],
        "dimension": rule["dimension"],
        "severity": rule["severity"],
        "evaluation_status": status,
        "rows_checked": rows_checked,
        "rows_failed": rows_failed,
        "pass_rate": (
            None
            if rows_failed is None or rows_checked == 0
            else round(100 * (rows_checked - rows_failed) / rows_checked, 2)
        ),
        "note": note,
    }


def _write_quality_results(spark, config: MigrationConfig, results: list[dict]) -> str:
    """Append auditable DQ summaries.  Status prevents unavailable rules looking passed."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]
    from pyspark.sql.types import (  # type: ignore[import-not-found]
        DoubleType,
        LongType,
        StringType,
        StructField,
        StructType,
    )

    target = config.qualified("governance", "dq_results")
    schema = StructType(
        [
            StructField("run_id", StringType(), False),
            StructField("rule_id", StringType(), False),
            StructField("dataset", StringType(), False),
            StructField("column_name", StringType(), False),
            StructField("dimension", StringType(), False),
            StructField("severity", StringType(), False),
            StructField("evaluation_status", StringType(), False),
            StructField("rows_checked", LongType(), False),
            StructField("rows_failed", LongType(), True),
            StructField("pass_rate", DoubleType(), True),
            StructField("note", StringType(), True),
        ]
    )
    frame = spark.createDataFrame(results, schema=schema).withColumn("checked_at", sf.current_timestamp())
    frame.write.format("delta").mode("append").saveAsTable(target)
    return target


def _write_quarantine(spark, config: MigrationConfig, run_id: str, failure_frames: list[tuple[dict, object]]) -> str:
    """Persist failing error rows without deleting them from the published Silver table."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]
    from pyspark.sql.types import (  # type: ignore[import-not-found]
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    target = config.qualified("governance", "quarantine")
    schema = StructType(
        [
            StructField("run_id", StringType(), False),
            StructField("dataset", StringType(), False),
            StructField("natural_key", StringType(), True),
            StructField("record", StringType(), True),
            StructField("rule_id", StringType(), False),
            StructField("reason", StringType(), False),
            StructField("quarantined_at", TimestampType(), False),
            StructField("resolved_at", TimestampType(), True),
            StructField("resolution_note", StringType(), True),
        ]
    )
    output = None
    for rule, failed in failure_frames:
        key_columns = rule.get("params", {}).get(
            "key_columns",
            ["tanggal", "kode_provinsi_bps", "kode_kabkota_bps", "komoditas_id", "jenis_pasar", "source"],
        )
        row = failed.select(
            sf.lit(run_id).alias("run_id"),
            sf.lit(rule["dataset"]).alias("dataset"),
            sf.concat_ws("|", *[sf.coalesce(sf.col(key).cast("string"), sf.lit("")) for key in key_columns]).alias("natural_key"),
            sf.to_json(sf.struct(*[sf.col(column) for column in failed.columns])).alias("record"),
            sf.lit(rule["rule_id"]).alias("rule_id"),
            sf.lit(rule["description"]).alias("reason"),
            sf.current_timestamp().alias("quarantined_at"),
            sf.lit(None).cast("timestamp").alias("resolved_at"),
            sf.lit(None).cast("string").alias("resolution_note"),
        )
        output = row if output is None else output.unionByName(row)
    if output is None:
        output = spark.createDataFrame([], schema=schema)
    output.write.format("delta").mode("append").saveAsTable(target)
    return target


def run_harga_pangan_quality(spark, config: MigrationConfig, run_id: str) -> dict[str, object]:
    """Evaluate HDX/WFP price DQ honestly and return blocking rule IDs for Gold gating."""
    from pyspark.sql import Window  # type: ignore[import-not-found]
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    frame = spark.table(config.qualified("silver", "harga_pangan"))
    rows_checked = frame.count()
    results: list[dict] = []
    failure_frames: list[tuple[dict, object]] = []
    for rule in harga_pangan_rules():
        kind = rule["type"]
        if kind == "in_reference":
            if rule["rule_id"] == "HP-006":
                failed = frame.where(
                    (sf.col("kode_provinsi_bps") != "00")
                    & ~sf.col("kode_provinsi_bps").isin(
                        [
                            row["kode_bps"]
                            for row in spark.table(
                                config.qualified("reference", "ref_provinsi")
                            ).select("kode_bps").collect()
                        ]
                    )
                )
            elif rule["rule_id"] == "HP-007":
                failed = frame.join(
                    spark.table(config.qualified("reference", "ref_komoditas")).select(
                        "komoditas_id"
                    ),
                    "komoditas_id",
                    "left_anti",
                )
            else:
                failed = None
            if failed is not None:
                failed_count = failed.count()
                results.append(
                    _rule_result(
                        rule,
                        run_id,
                        rows_checked,
                        failed_count,
                        "FAILED" if failed_count else "PASSED",
                        "Validated against the committed PanganWatch reference seed.",
                    )
                )
                if rule["severity"] == "error" and failed_count:
                    failure_frames.append((rule, failed))
                continue
            results.append(
                _rule_result(
                    rule,
                    run_id,
                    rows_checked,
                    None,
                    "BLOCKED_REFERENCE",
                    "Reference table has not been migrated; this error rule cannot be claimed as passed.",
                )
            )
            continue
        if kind == "range" and "max_future_days" in rule.get("params", {}):
            failed = frame.where(sf.col(rule["column"]) > sf.current_date())
        elif kind == "max_pct_change":
            params = rule["params"]
            window = Window.partitionBy(*params["partition_by"]).orderBy(params["order_by"])
            failed = (
                frame.withColumn("_previous_value", sf.lag(rule["column"]).over(window))
                .where(sf.col("_previous_value").isNotNull() & (sf.col("_previous_value") != 0))
                .where(
                    sf.abs((sf.col(rule["column"]) - sf.col("_previous_value")) / sf.col("_previous_value"))
                    * 100
                    > sf.lit(params["max_pct"])
                )
                .drop("_previous_value")
            )
        elif kind == "freshness":
            latest = frame.select(sf.max(rule["column"]).alias("latest")).first()["latest"]
            is_stale = latest is None or latest < __import__("datetime").date.today() - __import__("datetime").timedelta(days=rule["params"]["max_lag_days"])
            results.append(
                _rule_result(
                    rule,
                    run_id,
                    1,
                    int(is_stale),
                    "FAILED" if is_stale else "PASSED",
                    f"Latest source date: {latest!s}",
                )
            )
            continue
        elif kind == "completeness_ratio":
            params = rule["params"]
            scoped = frame
            if "filter" in params:
                source_filter = params["filter"]
                scoped = scoped.where(sf.col(source_filter["column"]).isin(source_filter["values"]))
            expected = params.get("expected_distinct", 38)
            grouped = scoped.groupBy(params["group_by"]).agg(
                sf.countDistinct(params["target_column"]).alias("_observed")
            )
            checked = grouped.count()
            if checked == 0:
                results.append(_rule_result(rule, run_id, 0, None, "NOT_APPLICABLE", "No rows match this coverage scope."))
                continue
            failed = grouped.where(sf.col("_observed") / sf.lit(expected) < sf.lit(params["min_ratio"]))
            failed_count = failed.count()
            results.append(
                _rule_result(rule, run_id, checked, failed_count, "FAILED" if failed_count else "PASSED", f"Expected distinct coverage: {expected}."))
            continue
        elif kind == "cross_source_diff":
            source_count = frame.select("source").distinct().count()
            results.append(
                _rule_result(rule, run_id, source_count, None, "NOT_APPLICABLE", "Cross-source comparison requires at least two sources.")
            )
            continue
        else:
            failed = evaluate_rule(frame, rule)

        failed_count = failed.count()
        results.append(
            _rule_result(rule, run_id, rows_checked, failed_count, "FAILED" if failed_count else "PASSED", rule["description"])
        )
        if rule["severity"] == "error" and failed_count:
            failure_frames.append((rule, failed))

    results_target = _write_quality_results(spark, config, results)
    quarantine_target = _write_quarantine(spark, config, run_id, failure_frames)
    blocking_rules = [
        item["rule_id"]
        for item in results
        if item["severity"] == "error" and item["evaluation_status"] != "PASSED"
    ]
    return {
        "dq_results_table": results_target,
        "quarantine_table": quarantine_target,
        "evaluated_rules": len(results),
        "blocking_rules": blocking_rules,
        "warning_failures": [
            item["rule_id"]
            for item in results
            if item["severity"] == "warn" and item["evaluation_status"] == "FAILED"
        ],
    }
