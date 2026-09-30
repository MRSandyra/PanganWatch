"""Generate glossary.md from governance_glossary seed."""

import csv
from pathlib import Path

SEED_PATH = Path("dbt/panganwatch/seeds/governance_glossary.csv")
OUTPUT_PATH = Path("docs/governance/glossary.md")


def main():
    rows = []
    with open(SEED_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    lines = [
        "# Glossary",
        "",
        f"Generated from `{SEED_PATH}` — **{len(rows)} terms**",
        "",
        "| Term | Definition | Domain | Owner | Related Columns | Source |",
        "|------|------------|--------|-------|-----------------|--------|",
    ]

    for row in sorted(rows, key=lambda x: x["term"]):
        lines.append(
            f"| {row['term']} | {row['definition']} | {row['domain']} | {row['owner']} | {row['related_columns']} | {row['source']} |"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Glossary written to {OUTPUT_PATH} ({len(rows)} terms)")


if __name__ == "__main__":
    main()
