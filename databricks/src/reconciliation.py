"""Exact-key, field-level reconciliation without arbitrary tolerances."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any


def reconcile_records(
    local: Iterable[dict[str, Any]],
    cloud: Iterable[dict[str, Any]],
    keys: list[str],
    tolerance: Decimal = Decimal("0"),
) -> list[dict[str, Any]]:
    def index(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, ...], dict[str, Any]]:
        return {tuple(str(row.get(key) or "") for key in keys): row for row in rows}

    left, right = index(local), index(cloud)
    findings = []
    for key in sorted(set(left) | set(right)):
        if key not in left or key not in right:
            findings.append(
                {
                    "business_key": dict(zip(keys, key)),
                    "field": "__record__",
                    "local_value": key in left,
                    "cloud_value": key in right,
                    "difference": None,
                    "classification": "MISSING_KEY",
                    "investigation_status": "OPEN",
                }
            )
            continue
        for field in sorted(set(left[key]) | set(right[key]) - set(keys)):
            a, b = left[key].get(field), right[key].get(field)
            if a is None and b is None:
                continue
            try:
                same = abs(Decimal(str(a)) - Decimal(str(b))) <= tolerance
                difference = str(Decimal(str(a)) - Decimal(str(b)))
            except Exception:
                same, difference = a == b, None
            if not same:
                findings.append(
                    {
                        "business_key": dict(zip(keys, key)),
                        "field": field,
                        "local_value": a,
                        "cloud_value": b,
                        "difference": difference,
                        "classification": "VALUE_MISMATCH",
                        "investigation_status": "OPEN",
                    }
                )
    return findings
