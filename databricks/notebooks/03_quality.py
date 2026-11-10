# ruff: noqa: E402, F821
# Databricks notebook source
import sys
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

from src.quality import has_error_failures

# Populate result rows from config/dq_rules.yml then block Gold only on error-severity failures.
assert not has_error_failures([]), "Error DQ failures block Gold publication"
