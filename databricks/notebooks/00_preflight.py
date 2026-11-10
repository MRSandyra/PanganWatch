# ruff: noqa: E402, F821
# Databricks notebook source
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath

# `databricks` is an installed vendor package in the workspace. Derive this
# Git folder's `databricks/` directory and import the local `src` package.
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
relative_project_dir = str(PurePosixPath(notebook_path).parent.parent)
candidate_dirs = [relative_project_dir]
if not relative_project_dir.startswith("/Workspace/"):
    candidate_dirs.append(f"/Workspace{relative_project_dir}")
project_databricks_dir = next(
    (directory for directory in candidate_dirs if (Path(directory) / "src" / "config.py").is_file()),
    None,
)
if project_databricks_dir is None:
    raise RuntimeError(
        "PanganWatch src/config.py was not found. "
        f"notebook_path={notebook_path!r}; candidates={candidate_dirs!r}"
    )
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

from src.config import load_config

dbutils.widgets.text("catalog", "", "Unity Catalog")
catalog = dbutils.widgets.get("catalog").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
config = replace(load_config(), catalog=catalog)
spark.sql("SELECT current_user(), current_catalog(), current_schema()").show(truncate=False)
for schema in config.schemas.values():
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{schema}")
spark.sql(
    f"CREATE VOLUME IF NOT EXISTS {config.catalog}.{config.schemas['landing']}.{config.volume}"
)
print({"status": "CLOUD_PREFLIGHT_VERIFIED", "volume_path": config.volume_path})
