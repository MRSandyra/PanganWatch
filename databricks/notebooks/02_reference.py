# ruff: noqa: E402, F821
# Databricks notebook source
# Load committed PanganWatch reference seeds before mapping source-native Bronze data.
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

from src.config import load_config
from src.reference import load_reference_seeds

dbutils.widgets.text("catalog", "", "Unity Catalog")
catalog = dbutils.widgets.get("catalog").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
config = replace(load_config(), catalog=catalog)
print(load_reference_seeds(spark, config))
