"""Report gold-layer columns without a description, from dbt's manifest.json.

Run `dbt docs generate` first so `dbt/panganwatch/target/manifest.json` exists.
Exit code is 0 iff every column of every gold model has a non-empty description.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MANIFEST_PATH = Path("dbt/panganwatch/target/manifest.json")


def find_undocumented_gold_columns(manifest: dict) -> list[tuple[str, str]]:
    """Returns (model_name, column_name) pairs missing a description, for
    enabled models materialized in the 'gold' schema."""
    missing: list[tuple[str, str]] = []
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") != "model":
            continue
        if node.get("config", {}).get("schema") != "gold":
            continue
        model_name = node.get("name", "unknown")
        if not (node.get("description") or "").strip():
            missing.append((model_name, "<model description>"))
        for col_name, col in node.get("columns", {}).items():
            if not (col.get("description") or "").strip():
                missing.append((model_name, col_name))
    return missing


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run `dbt docs generate` first.")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    missing = find_undocumented_gold_columns(manifest)

    if not missing:
        print("0 gold columns without a description.")
        return 0

    print(f"{len(missing)} gold columns without a description:")
    for model_name, col_name in missing:
        print(f"  - {model_name}.{col_name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
