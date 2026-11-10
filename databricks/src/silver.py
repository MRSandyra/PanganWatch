"""Typed Silver transforms and deterministic business-key de-duplication."""

from __future__ import annotations

from .config import MigrationConfig
from .schemas import spark_schema

KEYS = {
    "harga_pangan": [
        "tanggal",
        "kode_provinsi_bps",
        "kode_kabkota_bps",
        "komoditas_id",
        "jenis_pasar",
        "source",
    ],
    "cuaca_harian": ["tanggal", "kode_provinsi_bps"],
    "inflasi_kota": ["bulan", "kode_vervar"],
}


def deduplicate(frame, keys: list[str]):
    """Pick the newest ingestion record per business key deterministically."""
    from pyspark.sql import Window  # type: ignore[import-not-found]
    from pyspark.sql import functions as sf

    order = [sf.col("_ingested_at").desc_nulls_last(), sf.col("_source_sha256").desc_nulls_last()]
    return (
        frame.withColumn(
            "_row_number", sf.row_number().over(Window.partitionBy(*keys).orderBy(*order))
        )
        .where(sf.col("_row_number") == 1)
        .drop("_row_number")
    )


def write_silver(spark, config: MigrationConfig, dataset: str, frame, run_id: str) -> str:
    """Enforce schema casts then MERGE. Input must already contain resolved reference IDs."""
    from delta.tables import DeltaTable  # type: ignore[import-not-found]
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    target = config.qualified("silver", dataset)
    schema = spark_schema(dataset)
    typed = frame
    for field in schema.fields:
        if field.name == "loaded_at":
            typed = typed.withColumn(field.name, sf.current_timestamp())
        elif field.name == "run_id":
            typed = typed.withColumn(field.name, sf.lit(run_id))
        else:
            typed = typed.withColumn(field.name, sf.col(field.name).cast(field.dataType))
    typed = deduplicate(typed.select(*[f.name for f in schema.fields]), KEYS[dataset])
    if not spark.catalog.tableExists(target):
        typed.write.format("delta").mode("overwrite").saveAsTable(target)
        return target
    predicate = " AND ".join(f"t.{key} <=> s.{key}" for key in KEYS[dataset])
    DeltaTable.forName(spark, target).alias("t").merge(
        typed.alias("s"), predicate
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
    return target
