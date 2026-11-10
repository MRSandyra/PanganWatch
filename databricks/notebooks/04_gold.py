# ruff: noqa: E402, F821
# Databricks notebook source
import sys
from dataclasses import replace
from pathlib import PurePosixPath

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
project_databricks_dir = str(PurePosixPath(notebook_path).parent.parent)
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

from src.config import load_config
from src.gold import build_gold

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("run_id", "", "Run ID")
catalog = dbutils.widgets.get("catalog").strip()
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
config = replace(load_config(), catalog=catalog)
run_id = dbutils.widgets.get("run_id")
build_gold(spark, config, run_id)
