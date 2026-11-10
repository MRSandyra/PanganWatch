# ruff: noqa: E402, F821
# Databricks notebook source
# This thin notebook intentionally delegates typed MERGE logic to databricks.src.silver.
import sys
from pathlib import PurePosixPath

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
project_databricks_dir = str(PurePosixPath(notebook_path).parent.parent)
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

from src.config import load_config

config = load_config()
print(
    "Select the source-native Bronze table and call write_silver with its mapped, normalized frame."
)
