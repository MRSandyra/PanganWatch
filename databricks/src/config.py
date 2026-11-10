"""Validated configuration for workspace-neutral Databricks resource names."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ROOT = Path(__file__).resolve().parents[2]


def _identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


@dataclass(frozen=True)
class MigrationConfig:
    catalog: str | None
    schemas: dict[str, str]
    volume: str
    timezone: str
    snapshot_root: Path
    raw: dict[str, Any]

    def qualified(self, layer: str, table: str) -> str:
        catalog = self.catalog or "<PANGANWATCH_CATALOG>"
        return f"{catalog}.{self.schemas[layer]}.{_identifier(table, 'table')}"

    @property
    def volume_path(self) -> str:
        catalog = self.catalog or "<PANGANWATCH_CATALOG>"
        return f"/Volumes/{catalog}/{self.schemas['landing']}/{self.volume}"


def load_config(path: Path | None = None, environ: dict[str, str] | None = None) -> MigrationConfig:
    path = path or ROOT / "config" / "migration.yml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    env = environ or os.environ
    catalog = env.get(raw["catalog_env"])
    if catalog:
        _identifier(catalog, "catalog")
    schemas = {key: _identifier(value, f"schema {key}") for key, value in raw["schemas"].items()}
    return MigrationConfig(
        catalog=catalog,
        schemas=schemas,
        volume=_identifier(raw["volume"], "volume"),
        timezone=raw["timezone"],
        snapshot_root=ROOT.parent / raw["snapshot_root"],
        raw=raw,
    )
