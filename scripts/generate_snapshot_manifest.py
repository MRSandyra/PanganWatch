"""Create an immutable manifest for a local migration snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from databricks.src.manifest import build_manifest, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--period-start")
    parser.add_argument("--period-end")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(
        args.file,
        source_name=args.source_name,
        source_url=args.source_url,
        license_name=args.license,
        source_period_start=args.period_start,
        source_period_end=args.period_end,
    )
    output = args.output or args.file.with_suffix(args.file.suffix + ".manifest.json")
    write_manifest(manifest, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
