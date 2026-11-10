"""Explicit Spark schemas. Importing this module does not require PySpark locally."""

from __future__ import annotations

SCHEMA_SPECS = {
    "harga_pangan": [
        ("tanggal", "date", False),
        ("kode_provinsi_bps", "string", False),
        ("kode_kabkota_bps", "string", True),
        ("komoditas_id", "string", False),
        ("jenis_pasar", "string", False),
        ("harga", "decimal(12,2)", False),
        ("satuan", "string", False),
        ("source", "string", False),
        ("run_id", "string", False),
        ("loaded_at", "timestamp", False),
    ],
    "cuaca_harian": [
        ("tanggal", "date", False),
        ("kode_provinsi_bps", "string", False),
        ("precipitation_mm", "decimal(6,2)", True),
        ("tmax_c", "decimal(5,2)", True),
        ("tmin_c", "decimal(5,2)", True),
        ("source", "string", False),
        ("run_id", "string", False),
        ("loaded_at", "timestamp", False),
    ],
    "inflasi_kota": [
        ("bulan", "date", False),
        ("kode_vervar", "int", False),
        ("nama_kota", "string", False),
        ("ihk", "decimal(10,2)", False),
        ("inflasi_mtm", "decimal(8,2)", True),
        ("inflasi_yoy", "decimal(8,2)", True),
        ("source", "string", False),
        ("run_id", "string", False),
        ("loaded_at", "timestamp", False),
    ],
}


def spark_schema(name: str):
    """Return a StructType lazily so offline manifest tests need no PySpark install."""
    try:
        from pyspark.sql.types import (  # type: ignore[import-not-found]
            DateType,
            DecimalType,
            IntegerType,
            StringType,
            StructField,
            StructType,
            TimestampType,
        )
    except ImportError as exc:  # pragma: no cover - exercised in Databricks
        raise RuntimeError("PySpark is required only for Spark transformations") from exc
    types = {"date": DateType, "string": StringType, "int": IntegerType, "timestamp": TimestampType}
    fields = []
    for column, type_name, nullable in SCHEMA_SPECS[name]:
        if type_name.startswith("decimal"):
            precision, scale = map(int, type_name[8:-1].split(","))
            data_type = DecimalType(precision, scale)
        else:
            data_type = types[type_name]()
        fields.append(StructField(column, data_type, nullable))
    return StructType(fields)
