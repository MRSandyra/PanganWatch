# ruff: noqa: E402, F821
# Databricks notebook source
# HDX/WFP mapping policy: only explicit National Average rows map to BPS code 00.
# Rows with unapproved geography stay in Bronze and are recorded in governance.
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
from src.silver import publish_hdx_wfp_prices

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("run_id", "", "Run ID")
dbutils.widgets.dropdown("rebuild_hdx_wfp", "false", ["false", "true"], "Rebuild HDX/WFP Silver")
catalog = dbutils.widgets.get("catalog").strip()
run_id = dbutils.widgets.get("run_id").strip()
rebuild_hdx_wfp = dbutils.widgets.get("rebuild_hdx_wfp") == "true"
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
assert run_id, "Provide a run ID, for example 20261110_hdx_wfp_01."
config = replace(load_config(), catalog=catalog)
print(publish_hdx_wfp_prices(spark, config, run_id, rebuild_hdx_wfp=rebuild_hdx_wfp))
