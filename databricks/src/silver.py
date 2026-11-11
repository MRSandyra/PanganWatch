"""Typed Silver transforms and deterministic business-key de-duplication."""

from __future__ import annotations

from .config import MigrationConfig
from .schemas import spark_schema

HDX_WFP_NATIONAL_MARKET = "national average"
HDX_WFP_NATIONAL_PROVINCE_CODE = "00"
HDX_WFP_GOVERNANCE_COLUMNS = [
    "date",
    "admin1",
    "admin2",
    "market",
    "market_id",
    "latitude",
    "longitude",
    "category",
    "commodity",
    "commodity_id",
    "unit",
    "priceflag",
    "pricetype",
    "currency",
    "price",
    "usdprice",
    "_snapshot_id",
    "_source_sha256",
    "_source_url",
    "_ingested_at",
]

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
    # Deduplicate while Bronze provenance is still present.  The public Silver
    # schema intentionally excludes those metadata columns, so selecting the
    # contract fields must happen only after the deterministic ordering.
    typed = deduplicate(typed, KEYS[dataset]).select(*[f.name for f in schema.fields])
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


def split_hdx_wfp_prices(spark, config: MigrationConfig, frame):
    """Map WFP rows through committed HDX aliases without inventing identifiers."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    province_alias = (
        spark.table(config.qualified("reference", "ref_provinsi_alias"))
        .where(sf.col("sumber") == "HDX")
        .select(
            sf.col("nama_sumber").alias("_admin1"),
            sf.col("kode_bps").alias("_kode_provinsi_bps"),
        )
    )
    commodity_alias = (
        spark.table(config.qualified("reference", "ref_komoditas_alias"))
        .where(sf.col("sumber") == "HDX")
        .select(
            sf.col("nama_sumber").alias("_commodity"),
            sf.col("komoditas_id").alias("_komoditas_id"),
        )
    )
    enriched = (
        frame.join(province_alias, frame.admin1 == province_alias._admin1, "left")
        .join(commodity_alias, frame.commodity == commodity_alias._commodity, "left")
    )
    national = _hdx_wfp_is_national(sf)
    accepted = enriched.where(national | sf.col("_kode_provinsi_bps").isNotNull()).where(
        sf.col("_komoditas_id").isNotNull()
    )
    mapped = accepted.select(
        sf.to_date(sf.col("date")).alias("tanggal"),
        sf.when(national, sf.lit(HDX_WFP_NATIONAL_PROVINCE_CODE))
        .otherwise(sf.col("_kode_provinsi_bps"))
        .alias("kode_provinsi_bps"),
        sf.lit(None).cast("string").alias("kode_kabkota_bps"),
        sf.col("_komoditas_id").cast("string").alias("komoditas_id"),
        sf.trim(sf.col("market")).alias("jenis_pasar"),
        sf.col("price").alias("harga"),
        sf.concat(sf.lit("rupiah/"), sf.trim(sf.col("unit"))).alias("satuan"),
        sf.lit("hdx_wfp").alias("source"),
        sf.col("_ingested_at"),
        sf.col("_source_sha256"),
    )
    unmapped = enriched.where(~(national | sf.col("_kode_provinsi_bps").isNotNull()) | sf.col("_komoditas_id").isNull()).withColumn(
        "_exclusion_reason",
        sf.when(
            sf.col("_komoditas_id").isNull(),
            sf.lit("WFP commodity has no approved canonical commodity alias."),
        ).otherwise(sf.lit("WFP geography has no approved BPS crosswalk.")),
    )
    return mapped, unmapped


def record_hdx_wfp_unmapped_geography(spark, config: MigrationConfig, frame, run_id: str) -> str:
    """Persist excluded WFP rows idempotently for later BPS-crosswalk resolution."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    target = config.qualified("governance", "hdx_wfp_unmapped_geography")
    records = (
        frame.select(
            *[sf.col(column) for column in HDX_WFP_GOVERNANCE_COLUMNS],
            sf.col("_exclusion_reason"),
        )
        .withColumn("_run_id", sf.lit(run_id))
        .withColumn(
            "_record_key",
            sf.sha2(
                sf.to_json(sf.struct(*[sf.col(column) for column in HDX_WFP_GOVERNANCE_COLUMNS])),
                256,
            ),
        )
    )
    if spark.catalog.tableExists(target):
        existing = spark.table(target).select("_snapshot_id", "_record_key")
        records = records.join(existing, ["_snapshot_id", "_record_key"], "left_anti")
    records.write.format("delta").mode("append").saveAsTable(target)
    return target


def publish_hdx_wfp_prices(
    spark, config: MigrationConfig, run_id: str, *, rebuild_hdx_wfp: bool = False
) -> dict[str, object]:
    """Publish alias-resolved WFP prices and retain unmapped rows visibly."""
    bronze = config.qualified("bronze", "hdx_wfp_raw")
    raw = spark.table(bronze)
    target = config.qualified("silver", "harga_pangan")
    if spark.catalog.tableExists(target) and not rebuild_hdx_wfp:
        reference_ids = spark.table(config.qualified("reference", "ref_komoditas")).select(
            "komoditas_id"
        )
        provisional_rows = (
            spark.table(target)
            .where("source = 'hdx_wfp'")
            .join(reference_ids, "komoditas_id", "left_anti")
            .limit(1)
            .count()
        )
        if provisional_rows:
            raise RuntimeError(
                "Set rebuild_hdx_wfp=true once to replace provisional HDX/WFP Silver rows "
                "whose commodity IDs have not been resolved through the committed aliases."
            )
    replaced_rows = 0
    if rebuild_hdx_wfp and spark.catalog.tableExists(target):
        replaced_rows = spark.table(target).where("source = 'hdx_wfp'").count()
        spark.sql(f"DELETE FROM {target} WHERE source = 'hdx_wfp'")
    mapped, unmapped = split_hdx_wfp_prices(spark, config, raw)
    silver_target = write_silver(spark, config, "harga_pangan", mapped, run_id)
    if rebuild_hdx_wfp:
        snapshot_ids = [row["_snapshot_id"] for row in raw.select("_snapshot_id").distinct().collect()]
        unmapped_target = config.qualified("governance", "hdx_wfp_unmapped_geography")
        if spark.catalog.tableExists(unmapped_target) and snapshot_ids:
            quoted = ", ".join(repr(value) for value in snapshot_ids)
            spark.sql(f"DELETE FROM {unmapped_target} WHERE _snapshot_id IN ({quoted})")
    unmapped_target = record_hdx_wfp_unmapped_geography(spark, config, unmapped, run_id)
    return {
        "bronze_table": bronze,
        "silver_table": silver_target,
        "unmapped_governance_table": unmapped_target,
        "silver_rows_for_run": mapped.count(),
        "unmapped_rows_for_run": unmapped.count(),
        "replaced_provisional_hdx_wfp_rows": replaced_rows,
        "mapping_policy": "Committed HDX province and commodity aliases; National Average -> code 00; unmapped values retained in governance.",
    }
