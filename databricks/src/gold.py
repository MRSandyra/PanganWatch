"""Gold marts ported from dbt definitions with explicit Spark-compatible semantics."""

from __future__ import annotations

from .config import MigrationConfig


def build_gold(spark, config: MigrationConfig, run_id: str) -> list[str]:
    """Publish staged Gold tables only after the caller has passed the error DQ gate."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    prices = spark.table(config.qualified("silver", "harga_pangan"))
    weather = spark.table(config.qualified("silver", "cuaca_harian"))
    gold = config.schemas["gold"]
    catalog = config.catalog or "<PANGANWATCH_CATALOG>"
    fct = (
        prices.groupBy("tanggal", "kode_provinsi_bps", "komoditas_id", "jenis_pasar", "source")
        .agg(
            sf.expr("percentile(harga, 0.5)").alias("harga_median"),
            sf.min("harga").alias("harga_min"),
            sf.max("harga").alias("harga_max"),
            sf.count("*").alias("n_observasi"),
        )
        .withColumn("n_dq_warn", sf.lit(0))
    )
    fct_target = f"{catalog}.{gold}.fct_harga_bulanan_staging_{run_id.replace('-', '_')}"
    fct.write.format("delta").mode("overwrite").saveAsTable(fct_target)
    monthly = (
        fct.withColumn("bulan", sf.trunc("tanggal", "month"))
        .groupBy("bulan", "kode_provinsi_bps", "komoditas_id")
        .agg(sf.expr("percentile(harga_median, 0.5)").alias("harga_median_provinsi"))
    )
    national = monthly.groupBy("bulan", "komoditas_id").agg(
        sf.expr("percentile(harga_median_provinsi, 0.5)").alias("harga_median_nasional")
    )
    disparity = monthly.join(national, ["bulan", "komoditas_id"]).withColumn(
        "pct_deviasi",
        sf.round(
            100
            * (sf.col("harga_median_provinsi") - sf.col("harga_median_nasional"))
            / sf.col("harga_median_nasional"),
            2,
        ),
    )
    weather_monthly = (
        weather.withColumn("bulan", sf.trunc("tanggal", "month"))
        .groupBy("bulan", "kode_provinsi_bps")
        .agg(
            sf.sum(sf.when(sf.col("precipitation_mm") >= 50, 1).otherwise(0)).alias(
                "hari_hujan_lebat"
            ),
            sf.sum("precipitation_mm").alias("total_hujan_mm"),
        )
    )
    targets = {
        "fct_harga_bulanan": fct,
        "mart_disparitas_provinsi": disparity,
        "mart_cuaca_harga_bulanan": weather_monthly,
    }
    published = []
    for name, frame in targets.items():
        stage = f"{catalog}.{gold}.{name}_staging_{run_id.replace('-', '_')}"
        target = f"{catalog}.{gold}.{name}"
        frame.write.format("delta").mode("overwrite").saveAsTable(stage)
        spark.sql(f"CREATE OR REPLACE TABLE {target} AS SELECT * FROM {stage}")
        published.append(target)
    return published
