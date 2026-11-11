# ruff: noqa: E402, F821
# Databricks notebook source
import importlib
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

import src.quality as quality_module
from src.config import load_config

importlib.reload(quality_module)
from src.quality import run_cuaca_harian_quality, run_harga_pangan_quality

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("run_id", "", "Run ID")
catalog = dbutils.widgets.get("catalog").strip()
run_id = dbutils.widgets.get("run_id").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
assert run_id, "Provide the same run ID used by 02_silver."
config = replace(load_config(), catalog=catalog)
price_summary = run_harga_pangan_quality(spark, config, run_id)
weather_summary = run_cuaca_harian_quality(spark, config, run_id)
summary = {
    "harga_pangan": price_summary,
    "cuaca_harian": weather_summary,
    "blocking_rules": price_summary["blocking_rules"] + weather_summary["blocking_rules"],
}
print(summary)
assert not summary["blocking_rules"], f"Gold is blocked by DQ rules: {summary['blocking_rules']}"
