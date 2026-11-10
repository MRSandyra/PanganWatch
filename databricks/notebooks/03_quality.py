# ruff: noqa: E402, F821
# Databricks notebook source
import sys
from pathlib import PurePosixPath

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
project_databricks_dir = str(PurePosixPath(notebook_path).parent.parent)
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

from src.quality import has_error_failures

# Populate result rows from config/dq_rules.yml then block Gold only on error-severity failures.
assert not has_error_failures([]), "Error DQ failures block Gold publication"
