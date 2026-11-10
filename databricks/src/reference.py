"""Load versioned legacy reference seeds into project-only Unity Catalog tables."""

from __future__ import annotations

import csv

from .config import MigrationConfig
from .quality import ROOT

SEED_DIRECTORY = ROOT.parent / "dbt" / "panganwatch" / "seeds"
REFERENCE_SEEDS = (
    "ref_provinsi",
    "ref_komoditas",
    "ref_provinsi_alias",
    "ref_komoditas_alias",
)


def load_reference_seeds(spark, config: MigrationConfig) -> dict[str, object]:
    """Replace only reproducible reference tables from committed CSV seeds."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schemas['reference']}")
    published: dict[str, int] = {}
    for name in REFERENCE_SEEDS:
        path = SEED_DIRECTORY / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Required committed reference seed is missing: {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        target = config.qualified("reference", name)
        spark.createDataFrame(rows).write.format("delta").mode("overwrite").saveAsTable(target)
        published[target] = len(rows)
    return {"reference_schema": config.schemas["reference"], "tables": published}
