"""F3a: records that fail wilayah/komoditas mapping are not loaded to silver.

Written to data/tmp/unmapped_<run_id>.jsonl and counted as rows_quarantined.
From F4 onward these route to governance.quarantine instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = ROOT / "data" / "tmp"


def append_unmapped(run_id: str, dataset: str, record: dict[str, Any], reason: str) -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    path = TMP_DIR / f"unmapped_{run_id}.jsonl"
    entry = {"dataset": dataset, "reason": reason, "record": record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
