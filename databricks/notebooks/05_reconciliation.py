# ruff: noqa: E402, F401, F821
# Databricks notebook source
import sys
from pathlib import PurePosixPath

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
project_databricks_dir = str(PurePosixPath(notebook_path).parent.parent)
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

from src.reconciliation import reconcile_records

print("Use an identical frozen snapshot; store any reconciliation differences in pw_governance.")
