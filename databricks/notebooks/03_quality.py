# ruff: noqa: E402, F821
# Databricks notebook source
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
from src.quality import run_harga_pangan_quality

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("run_id", "", "Run ID")
catalog = dbutils.widgets.get("catalog").strip()
run_id = dbutils.widgets.get("run_id").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
assert run_id, "Provide the same run ID used by 02_silver."
config = replace(load_config(), catalog=catalog)
summary = run_harga_pangan_quality(spark, config, run_id)
print(summary)
assert not summary["blocking_rules"], f"Gold is blocked by DQ rules: {summary['blocking_rules']}"
