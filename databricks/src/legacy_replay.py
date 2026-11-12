"""Non-production replay of immutable snapshots recovered from legacy Bronze."""

from __future__ import annotations

from pathlib import Path

from .config import MigrationConfig
from .silver import KEYS, deduplicate, split_hdx_wfp_prices
from .weather import transform_open_meteo_daily


def _write_replay_table(spark, config: MigrationConfig, dataset: str, frame, run_id: str) -> str:
    """Write a typed replay table without touching production Silver."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    from .schemas import spark_schema

    typed = frame
    schema = spark_schema(dataset)
    for field in schema.fields:
        if field.name == "loaded_at":
            typed = typed.withColumn(field.name, sf.current_timestamp())
        elif field.name == "run_id":
            typed = typed.withColumn(field.name, sf.lit(run_id))
        else:
            typed = typed.withColumn(field.name, sf.col(field.name).cast(field.dataType))
    typed = deduplicate(typed, KEYS[dataset]).select(*[field.name for field in schema.fields])
    target = config.qualified("legacy_replay", dataset)
    typed.write.format("delta").mode("overwrite").saveAsTable(target)
    return target


def replay_legacy_snapshots(
    spark,
    config: MigrationConfig,
    *,
    price_manifest: dict,
    price_path: Path,
    weather_manifest: dict,
    weather_path: Path,
    run_id: str,
) -> dict[str, object]:
    """Map recovered raw snapshots to isolated replay tables.

    This avoids production Bronze and Silver, so it cannot replace the newer
    cloud snapshots or change the published dashboard.
    """
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    from .manifest import validate_manifest

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schemas['legacy_replay']}")
    validate_manifest(price_manifest, price_path)
    validate_manifest(weather_manifest, weather_path)

    price_raw = spark.read.option("header", "true").csv(str(price_path))
    price_raw = (
        price_raw.withColumn("_snapshot_id", sf.lit(price_manifest["snapshot_id"]))
        .withColumn("_source_sha256", sf.lit(price_manifest["sha256"]))
        .withColumn("_source_url", sf.lit(price_manifest["source_url"]))
        .withColumn("_ingested_at", sf.current_timestamp())
    )
    mapped_prices, _ = split_hdx_wfp_prices(spark, config, price_raw)
    price_target = _write_replay_table(spark, config, "harga_pangan", mapped_prices, run_id)

    weather_raw = spark.read.json(str(weather_path))
    weather_raw = (
        weather_raw.withColumn("_snapshot_id", sf.lit(weather_manifest["snapshot_id"]))
        .withColumn("_source_sha256", sf.lit(weather_manifest["sha256"]))
        .withColumn("_source_url", sf.lit(weather_manifest["source_url"]))
        .withColumn("_ingested_at", sf.current_timestamp())
    )
    weather_target = _write_replay_table(
        spark, config, "cuaca_harian", transform_open_meteo_daily(weather_raw), run_id
    )
    return {
        "price_replay_table": price_target,
        "weather_replay_table": weather_target,
        "price_snapshot_id": price_manifest["snapshot_id"],
        "weather_snapshot_id": weather_manifest["snapshot_id"],
        "production_tables_modified": False,
    }
