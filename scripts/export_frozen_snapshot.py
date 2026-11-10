"""Copy an explicitly selected permitted source extract into an ignored immutable snapshot folder."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from databricks.src.manifest import build_manifest, write_manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--source-name", required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--license", required=True)
    p.add_argument("--destination", type=Path, required=True)
    a = p.parse_args()
    if not a.source.is_file():
        raise FileNotFoundError(a.source)
    a.destination.mkdir(parents=True, exist_ok=True)
    target = a.destination / a.source.name
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite immutable snapshot: {target}")
    shutil.copy2(a.source, target)
    manifest = build_manifest(
        target, source_name=a.source_name, source_url=a.source_url, license_name=a.license
    )
    write_manifest(manifest, target.with_suffix(target.suffix + ".manifest.json"))
    print(manifest["snapshot_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
