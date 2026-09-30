"""Generate raci.md from governance_raci seed."""

import csv
from pathlib import Path

SEED_PATH = Path("dbt/panganwatch/seeds/governance_raci.csv")
OUTPUT_PATH = Path("docs/governance/raci.md")


def main() -> None:
    rows = []
    with open(SEED_PATH, newline="", encoding="utf-8") as f:
        rows.extend(csv.DictReader(f))

    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_dataset.setdefault(row["dataset"], []).append(row)

    lines = [
        "# RACI Matrix",
        "",
        f"Generated from `{SEED_PATH}` — **{len(by_dataset)} datasets** × 4 roles",
        "",
        "| Dataset | Data Owner | Data Steward | Data Custodian | Consumer |",
        "|---|---|---|---|---|",
    ]

    for dataset in sorted(by_dataset):
        roles = {row["role"]: row for row in by_dataset[dataset]}

        def cell(role: str) -> str:
            row = roles.get(role, {})
            value = row.get("raci_value", "")
            owner = row.get("owner", "")
            if owner:
                return f"{value} ({owner})"
            return value

        lines.append(
            f"| {dataset} | {cell('Data Owner')} | {cell('Data Steward')} | "
            f"{cell('Data Custodian')} | {cell('Consumer')} |"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"RACI matrix written to {OUTPUT_PATH} ({len(by_dataset)} datasets)")


if __name__ == "__main__":
    main()
