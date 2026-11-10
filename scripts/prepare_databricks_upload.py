"""Validate a snapshot before its owner uploads it to the approved UC Volume."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from databricks.src.config import load_config
from databricks.src.manifest import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--catalog",
        help="Verified Unity Catalog name; used only to render the target Volume path",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest, args.file)
    environ = {"PANGANWATCH_CATALOG": args.catalog} if args.catalog else None
    print(
        json.dumps(
            {
                "valid": True,
                "snapshot_id": manifest["snapshot_id"],
                "upload_destination": load_config(environ=environ).volume_path,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
