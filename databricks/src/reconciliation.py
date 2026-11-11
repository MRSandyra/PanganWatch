"""Exact-key, field-level reconciliation without arbitrary tolerances."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from .config import MigrationConfig


def reconcile_records(
    local: Iterable[dict[str, Any]],
    cloud: Iterable[dict[str, Any]],
    keys: list[str],
    tolerance: Decimal = Decimal("0"),
) -> list[dict[str, Any]]:
    def index(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, ...], dict[str, Any]]:
        return {tuple(str(row.get(key) or "") for key in keys): row for row in rows}

    left, right = index(local), index(cloud)
    findings = []
    for key in sorted(set(left) | set(right)):
        if key not in left or key not in right:
            findings.append(
                {
                    "business_key": dict(zip(keys, key)),
                    "field": "__record__",
                    "local_value": key in left,
                    "cloud_value": key in right,
                    "difference": None,
                    "classification": "MISSING_KEY",
                    "investigation_status": "OPEN",
                }
            )
            continue
        for field in sorted(set(left[key]) | set(right[key]) - set(keys)):
            a, b = left[key].get(field), right[key].get(field)
            if a is None and b is None:
                continue
            try:
                same = abs(Decimal(str(a)) - Decimal(str(b))) <= tolerance
                difference = str(Decimal(str(a)) - Decimal(str(b)))
            except Exception:
                same, difference = a == b, None
            if not same:
                findings.append(
                    {
                        "business_key": dict(zip(keys, key)),
                        "field": field,
                        "local_value": a,
                        "cloud_value": b,
                        "difference": difference,
                        "classification": "VALUE_MISMATCH",
                        "investigation_status": "OPEN",
                    }
                )
    return findings


COMPARISON_COLUMNS = {
    "harga_pangan": [
        "tanggal",
        "kode_provinsi_bps",
        "kode_kabkota_bps",
        "komoditas_id",
        "jenis_pasar",
        "harga",
        "satuan",
        "source",
    ],
    "cuaca_harian": [
        "tanggal",
        "kode_provinsi_bps",
        "precipitation_mm",
        "tmax_c",
        "tmin_c",
        "source",
    ],
}


def _comparison_frame(frame, dataset: str):
    """Cast a source replay into the same non-audit Silver fields as its target."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    from .schemas import spark_schema

    typed = frame
    schema_fields = {field.name: field for field in spark_schema(dataset).fields}
    for column in COMPARISON_COLUMNS[dataset]:
        typed = typed.withColumn(column, sf.col(column).cast(schema_fields[column].dataType))
    return typed.select(*COMPARISON_COLUMNS[dataset])


def _write_reconciliation_results(spark, config: MigrationConfig, run_id: str, results: list[dict]) -> str:
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]
    from pyspark.sql.types import (  # type: ignore[import-not-found]
        LongType,
        StringType,
        StructField,
        StructType,
    )

    target = config.qualified("governance", "reconciliation_results")
    schema = StructType(
        [
            StructField("run_id", StringType(), False),
            StructField("reconciliation_type", StringType(), False),
            StructField("dataset", StringType(), False),
            StructField("expected_rows", LongType(), False),
            StructField("actual_rows", LongType(), False),
            StructField("expected_missing_in_cloud", LongType(), False),
            StructField("unexpected_cloud_rows", LongType(), False),
            StructField("status", StringType(), False),
        ]
    )
    frame = spark.createDataFrame(results, schema=schema).withColumn("checked_at", sf.current_timestamp())
    frame.write.format("delta").mode("append").saveAsTable(target)
    return target


def run_source_replay_reconciliation(spark, config: MigrationConfig, run_id: str) -> dict[str, object]:
    """Reconcile both Silver tables against deterministic replays of their frozen Bronze inputs."""
    from .silver import split_hdx_wfp_prices
    from .weather import transform_open_meteo_daily

    expected = {
        "harga_pangan": _comparison_frame(
            split_hdx_wfp_prices(
                spark, config, spark.table(config.qualified("bronze", "hdx_wfp_raw"))
            )[0],
            "harga_pangan",
        ),
        "cuaca_harian": _comparison_frame(
            transform_open_meteo_daily(spark.table(config.qualified("bronze", "open_meteo_raw"))),
            "cuaca_harian",
        ),
    }
    results = []
    for dataset, expected_frame in expected.items():
        actual = spark.table(config.qualified("silver", dataset)).select(
            *COMPARISON_COLUMNS[dataset]
        )
        missing = expected_frame.exceptAll(actual).count()
        extra = actual.exceptAll(expected_frame).count()
        results.append(
            {
                "run_id": run_id,
                "reconciliation_type": "SOURCE_REPLAY",
                "dataset": dataset,
                "expected_rows": expected_frame.count(),
                "actual_rows": actual.count(),
                "expected_missing_in_cloud": missing,
                "unexpected_cloud_rows": extra,
                "status": "PASS" if missing == 0 and extra == 0 else "FAIL",
            }
        )
    target = _write_reconciliation_results(spark, config, run_id, results)
    return {
        "reconciliation_type": "SOURCE_REPLAY",
        "results_table": target,
        "datasets": results,
        "failed_datasets": [item["dataset"] for item in results if item["status"] != "PASS"],
    }
