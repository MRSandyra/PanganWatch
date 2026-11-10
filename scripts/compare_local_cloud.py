"""Compare JSON/JSONL local and cloud extracts at the declared business-key grain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from databricks.src.reconciliation import reconcile_records


def rows(path: Path):
    text = path.read_text(encoding="utf-8")
    value = (
        json.loads(text)
        if path.suffix == ".json"
        else [json.loads(x) for x in text.splitlines() if x.strip()]
    )
    return value if isinstance(value, list) else [value]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("local", type=Path)
    p.add_argument("cloud", type=Path)
    p.add_argument("--keys", required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    findings = reconcile_records(rows(a.local), rows(a.cloud), a.keys.split(","))
    body = {"status": "PASS" if not findings else "FAIL", "mismatches": findings}
    if a.output:
        a.output.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    print(json.dumps(body, indent=2, default=str))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
