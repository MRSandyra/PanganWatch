"""Generate data dictionary from dbt manifest.json and catalog.json."""

import csv
import json
from pathlib import Path

MANIFEST_PATH = Path("dbt/panganwatch/target/manifest.json")
CATALOG_PATH = Path("dbt/panganwatch/target/catalog.json")
RACI_PATH = Path("dbt/panganwatch/seeds/governance_raci.csv")
OUTPUT_PATH = Path("docs/data_dictionary.md")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_raci() -> dict[str, dict[str, str]]:
    raci: dict[str, dict[str, str]] = {}
    if not RACI_PATH.exists():
        return raci
    with open(RACI_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dataset = row["dataset"]
            raci.setdefault(dataset, {})[row["role"]] = row.get("owner", "") or row["raci_value"]
    return raci


def relation_name(node: dict) -> str:
    return f"{node.get('schema')}.{node.get('name')}"


def candidate_raci_keys(relation: str, node: dict) -> list[str]:
    name = node.get("name", "")
    schema = node.get("schema", "")
    keys = [relation, name]
    if schema == "gold":
        keys.append(f"gold.{name}")
    if schema == "staging":
        keys.append(f"staging.{name}")
    if schema == "ref":
        keys.append(f"ref.{name}")
    return keys


def owner_for(relation: str, node: dict, raci: dict[str, dict[str, str]]) -> str:
    for key in candidate_raci_keys(relation, node):
        roles = raci.get(key)
        if roles and roles.get("Data Owner"):
            return roles["Data Owner"]
    if relation.startswith("silver."):
        return "PanganWatch data platform"
    if relation.startswith("gold."):
        return "PanganWatch analytics"
    if relation.startswith("governance."):
        return "PanganWatch governance"
    if relation.startswith("ref."):
        return "PanganWatch reference data"
    return "PanganWatch"


def column_tests(manifest: dict, node_id: str, column_name: str) -> list[str]:
    tests = []
    for test_id, test_node in manifest.get("nodes", {}).items():
        if test_node.get("resource_type") != "test":
            continue
        parents = test_node.get("depends_on", {}).get("nodes", [])
        if node_id not in parents:
            continue
        kwargs = test_node.get("test_metadata", {}).get("kwargs", {})
        if kwargs.get("column_name") == column_name or test_node.get("column_name") == column_name:
            tests.append(test_node.get("name", test_id))
    return sorted(tests)


def table_tests(manifest: dict, node_id: str) -> list[str]:
    tests = []
    for test_id, test_node in manifest.get("nodes", {}).items():
        if test_node.get("resource_type") != "test":
            continue
        parents = test_node.get("depends_on", {}).get("nodes", [])
        if node_id not in parents:
            continue
        kwargs = test_node.get("test_metadata", {}).get("kwargs", {})
        if not kwargs.get("column_name") and not test_node.get("column_name"):
            tests.append(test_node.get("name", test_id))
    return sorted(tests)


def catalog_columns(catalog: dict, node_id: str) -> dict:
    if node_id in catalog.get("nodes", {}):
        return catalog["nodes"][node_id].get("columns", {})
    if node_id in catalog.get("sources", {}):
        return catalog["sources"][node_id].get("columns", {})
    return {}


def collect_relations(manifest: dict, catalog: dict) -> list[tuple[str, str, dict]]:
    relations = []
    for node_id, node in manifest.get("sources", {}).items():
        relations.append((node_id, "source", node))
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") in {"model", "seed"}:
            relations.append((node_id, node.get("resource_type", ""), node))

    def sort_key(item: tuple[str, str, dict]) -> tuple[int, str]:
        _, resource_type, node = item
        schema = node.get("schema", "")
        order = {
            "source": 0,
            "ref": 1,
            "silver": 2,
            "staging": 3,
            "gold": 4,
            "governance": 5,
        }.get(schema, 9)
        if resource_type == "source":
            order = 0
        return (order, relation_name(node))

    return sorted(relations, key=sort_key)


def generate_markdown(manifest: dict, catalog: dict, raci: dict[str, dict[str, str]]) -> str:
    lines = [
        "# Data Dictionary",
        "",
        "Generated from `dbt/panganwatch/target/manifest.json`, `catalog.json`, and `dbt/panganwatch/seeds/governance_raci.csv`.",
        "",
        "## Tables and Columns",
        "",
    ]

    for node_id, resource_type, node in collect_relations(manifest, catalog):
        relation = relation_name(node)
        materialized = node.get("config", {}).get("materialized", resource_type)
        description = node.get("description", "") or ""
        owner = owner_for(relation, node, raci)
        lines.extend(
            [
                f"### {relation}",
                "",
                f"**Resource type:** {resource_type}  ",
                f"**Materialization/type:** {materialized}  ",
                f"**Owner:** {owner}  ",
            ]
        )
        if description:
            lines.append(f"**Description:** {description}  ")
        tests = table_tests(manifest, node_id)
        if tests:
            lines.append(f"**Table tests:** {', '.join(tests)}  ")
        lines.extend(["", "| Column | Data Type | Description | Tests |", "|---|---|---|---|"])

        manifest_columns = node.get("columns", {})
        db_columns = catalog_columns(catalog, node_id)
        all_column_names = sorted(set(manifest_columns) | set(db_columns))
        for column_name in all_column_names:
            manifest_column = manifest_columns.get(column_name, {})
            catalog_column = db_columns.get(column_name, {})
            data_type = catalog_column.get("type") or manifest_column.get("data_type") or "unknown"
            column_description = (
                manifest_column.get("description") or catalog_column.get("comment") or ""
            )
            tests_text = ", ".join(column_tests(manifest, node_id, column_name))
            lines.append(f"| {column_name} | {data_type} | {column_description} | {tests_text} |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    catalog = load_json(CATALOG_PATH) if CATALOG_PATH.exists() else {"nodes": {}, "sources": {}}
    raci = load_raci()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(generate_markdown(manifest, catalog, raci), encoding="utf-8")
    print(f"Data dictionary written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
