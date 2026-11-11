"""Open-Meteo Archive envelope to typed daily weather Silver records."""

from __future__ import annotations

from .config import MigrationConfig
from .silver import write_silver


def transform_open_meteo_daily(frame):
    """Explode frozen raw API envelopes while retaining source checksum provenance."""
    from pyspark.sql import functions as sf  # type: ignore[import-not-found]

    exploded = frame.select(
        sf.col("requested_province.kode_provinsi_bps").alias("kode_provinsi_bps"),
        sf.posexplode(sf.col("response.daily.time")).alias("_position", "tanggal"),
        sf.col("response.daily.precipitation_sum").alias("_precipitation"),
        sf.col("response.daily.temperature_2m_max").alias("_tmax"),
        sf.col("response.daily.temperature_2m_min").alias("_tmin"),
        sf.col("_snapshot_id"),
        sf.col("_source_sha256"),
        sf.col("_ingested_at"),
    )
    return exploded.select(
        sf.to_date("tanggal").alias("tanggal"),
        "kode_provinsi_bps",
        sf.element_at("_precipitation", sf.col("_position") + 1).alias("precipitation_mm"),
        sf.element_at("_tmax", sf.col("_position") + 1).alias("tmax_c"),
        sf.element_at("_tmin", sf.col("_position") + 1).alias("tmin_c"),
        sf.lit("open_meteo_archive_era5").alias("source"),
        "_snapshot_id",
        "_source_sha256",
        "_ingested_at",
    )


def publish_open_meteo_weather(spark, config: MigrationConfig, run_id: str) -> dict[str, object]:
    """Publish daily weather from frozen Bronze envelopes through the shared Silver MERGE."""
    bronze = config.qualified("bronze", "open_meteo_raw")
    silver = write_silver(spark, config, "cuaca_harian", transform_open_meteo_daily(spark.table(bronze)), run_id)
    return {"bronze_table": bronze, "silver_table": silver}
