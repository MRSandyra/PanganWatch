"""Validate a snapshot before its owner uploads it to the approved UC Volume."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from databricks.src.config import load_config
from databricks.src.manifest import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest, args.file)
    print(
        json.dumps(
            {
                "valid": True,
                "snapshot_id": manifest["snapshot_id"],
                "upload_destination": load_config().volume_path,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
