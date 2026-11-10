# ruff: noqa: E402, F821
# Databricks notebook source
# Parameters: snapshot_manifest_path, local_file_path. Upload only after manifest validation.
import json
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath

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

from src.bronze import load_snapshot_to_bronze
from src.config import load_config

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("snapshot_manifest_path", "", "Manifest path")
dbutils.widgets.text("local_file_path", "", "Snapshot path")
catalog = dbutils.widgets.get("catalog").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
config = replace(load_config(), catalog=catalog)
manifest = json.loads(Path(dbutils.widgets.get("snapshot_manifest_path")).read_text())
load_snapshot_to_bronze(spark, config, manifest, Path(dbutils.widgets.get("local_file_path")))
