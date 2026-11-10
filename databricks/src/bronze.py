"""Snapshot-to-Bronze loading with immutable manifest traceability."""

from __future__ import annotations

from pathlib import Path

from .config import MigrationConfig
from .manifest import validate_manifest


def load_snapshot_to_bronze(
    spark, config: MigrationConfig, manifest: dict, local_file: Path
) -> str:
    """Validate and append a source-native file to managed Bronze Delta.

    The idempotency key is snapshot_id + payload checksum. A repeated snapshot is a no-op.
    """
    validate_manifest(manifest, local_file)
    target = config.qualified("bronze", f"{manifest['source_name']}_raw")
    source = manifest["file_format"]
    reader = spark.read.option("header", "true") if source == "csv" else spark.read
    frame = reader.csv(str(local_file)) if source == "csv" else reader.json(str(local_file))
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    framed = (
        frame.withColumn("_snapshot_id", sf.lit(manifest["snapshot_id"]))
        .withColumn("_source_sha256", sf.lit(manifest["sha256"]))
        .withColumn("_source_url", sf.lit(manifest["source_url"]))
        .withColumn("_ingested_at", sf.current_timestamp())
    )
    if spark.catalog.tableExists(target):
        if (
            spark.table(target)
            .where(sf.col("_snapshot_id") == manifest["snapshot_id"])
            .limit(1)
            .count()
        ):
            return target
    framed.write.format("delta").mode("append").saveAsTable(target)
    return target
