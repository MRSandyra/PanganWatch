"""Typed Silver transforms and deterministic business-key de-duplication."""

from __future__ import annotations

from .config import MigrationConfig
from .schemas import spark_schema

HDX_WFP_NATIONAL_MARKET = "national average"
HDX_WFP_NATIONAL_PROVINCE_CODE = "00"

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


def _hdx_wfp_is_national(sf):
    """Return the explicit WFP National Average predicate.

    HDX/WFP does not provide BPS geographic codes.  Only rows whose market is
    explicitly labelled ``National Average`` may use the agreed national BPS
    sentinel ``00``.  All other rows remain in Bronze and are recorded as
    unmapped instead of receiving an invented geographic code.
    """
    return sf.lower(sf.trim(sf.coalesce(sf.col("market"), sf.lit("")))) == sf.lit(
        HDX_WFP_NATIONAL_MARKET
    )


def split_hdx_wfp_prices(frame):
    """Map WFP raw columns to the harga_pangan contract without silent loss."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    national = _hdx_wfp_is_national(sf)
    mapped = frame.where(national).select(
        sf.to_date(sf.col("date")).alias("tanggal"),
        sf.lit(HDX_WFP_NATIONAL_PROVINCE_CODE).alias("kode_provinsi_bps"),
        sf.lit(None).cast("string").alias("kode_kabkota_bps"),
        sf.col("commodity_id").cast("string").alias("komoditas_id"),
        sf.trim(sf.col("pricetype")).alias("jenis_pasar"),
        sf.col("price").alias("harga"),
        sf.trim(sf.col("unit")).alias("satuan"),
        sf.lit("hdx_wfp").alias("source"),
    )
    unmapped = frame.where(~national).withColumn(
        "_exclusion_reason",
        sf.lit("WFP geography has no approved BPS crosswalk; retained outside Silver."),
    )
    return mapped, unmapped


def record_hdx_wfp_unmapped_geography(spark, config: MigrationConfig, frame, run_id: str) -> str:
    """Persist excluded WFP rows idempotently for later BPS-crosswalk resolution."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    target = config.qualified("governance", "hdx_wfp_unmapped_geography")
    records = (
        frame.withColumn("_run_id", sf.lit(run_id))
        .withColumn(
            "_record_key",
            sf.sha2(sf.to_json(sf.struct(*[sf.col(column) for column in frame.columns])), 256),
        )
    )
    if spark.catalog.tableExists(target):
        existing = spark.table(target).select("_snapshot_id", "_record_key")
        records = records.join(existing, ["_snapshot_id", "_record_key"], "left_anti")
    records.write.format("delta").mode("append").saveAsTable(target)
    return target


def publish_hdx_wfp_prices(spark, config: MigrationConfig, run_id: str) -> dict[str, object]:
    """Publish only approved national WFP data and retain unmapped rows visibly."""
    bronze = config.qualified("bronze", "hdx_wfp_raw")
    mapped, unmapped = split_hdx_wfp_prices(spark.table(bronze))
    silver_target = write_silver(spark, config, "harga_pangan", mapped, run_id)
    unmapped_target = record_hdx_wfp_unmapped_geography(spark, config, unmapped, run_id)
    return {
        "bronze_table": bronze,
        "silver_table": silver_target,
        "unmapped_governance_table": unmapped_target,
        "silver_rows_for_run": mapped.count(),
        "unmapped_rows_for_run": unmapped.count(),
        "geography_policy": "National Average -> kode_provinsi_bps=00; other rows retained as unmapped.",
    }
