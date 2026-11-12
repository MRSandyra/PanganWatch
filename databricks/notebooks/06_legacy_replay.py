# ruff: noqa: E402, F821
# Databricks notebook source
"""Build isolated legacy replay tables from recovered immutable snapshots."""

import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath

notebook_path = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
)
relative_project_dir = str(PurePosixPath(notebook_path).parent.parent)
candidate_dirs = [relative_project_dir]
if not relative_project_dir.startswith("/Workspace/"):
    candidate_dirs.append(f"/Workspace{relative_project_dir}")
project_databricks_dir = next(
    (
        directory
        for directory in candidate_dirs
        if (Path(directory) / "src" / "config.py").is_file()
    ),
    None,
)
if project_databricks_dir is None:
    raise RuntimeError(
        "PanganWatch src/config.py was not found. "
        f"notebook_path={notebook_path!r}; candidates={candidate_dirs!r}"
    )
if project_databricks_dir not in sys.path:
    sys.path.insert(0, project_databricks_dir)

import src.legacy_replay as legacy_replay_module
from src.config import load_config

importlib.reload(legacy_replay_module)
from src.legacy_replay import replay_legacy_snapshots

dbutils.widgets.text("catalog", "", "Unity Catalog")
dbutils.widgets.text("run_id", "", "Replay run ID")
dbutils.widgets.text("price_manifest_path", "", "Legacy WFP manifest path")
dbutils.widgets.text("price_snapshot_path", "", "Legacy WFP snapshot path")
dbutils.widgets.text("weather_manifest_path", "", "Legacy weather manifest path")
dbutils.widgets.text("weather_snapshot_path", "", "Legacy weather snapshot path")

catalog = dbutils.widgets.get("catalog").strip()
run_id = dbutils.widgets.get("run_id").strip()
price_manifest_path = Path(dbutils.widgets.get("price_manifest_path"))
price_snapshot_path = Path(dbutils.widgets.get("price_snapshot_path"))
weather_manifest_path = Path(dbutils.widgets.get("weather_manifest_path"))
weather_snapshot_path = Path(dbutils.widgets.get("weather_snapshot_path"))
assert catalog, "Provide the verified Unity Catalog name in the catalog widget."
assert run_id, "Provide a replay run ID."
for path in (
    price_manifest_path,
    price_snapshot_path,
    weather_manifest_path,
    weather_snapshot_path,
):
    assert path.is_file(), f"Recovered replay artifact was not found: {path}"

config = replace(load_config(), catalog=catalog)
print(
    replay_legacy_snapshots(
        spark,
        config,
        price_manifest=json.loads(price_manifest_path.read_text()),
        price_path=price_snapshot_path,
        weather_manifest=json.loads(weather_manifest_path.read_text()),
        weather_path=weather_snapshot_path,
        run_id=run_id,
    )
)
