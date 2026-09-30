"""Generate lineage documentation from dbt manifest.json."""

import json
from pathlib import Path

MANIFEST_PATH = Path("dbt/panganwatch/target/manifest.json")
OUTPUT_PATH = Path("docs/lineage.md")

EXTERNAL_TO_BRONZE = {
    "HDX WFP": "hdx_wfp_prices",
    "Open-Meteo Archive": "open_meteo_daily",
    "Open-Meteo Current": "open_meteo_current",
    "PIHPS/Panel Harga": "pihps_prices",
    "BPS WebAPI": "bps_inflation",
    "Wilayah source files": "wilayah_raw",
}

BRONZE_TO_CANONICAL = {
    "hdx_wfp_prices": "silver.harga_pangan",
    "open_meteo_daily": "silver.cuaca_harian",
    "open_meteo_current": "silver.cuaca_terkini",
    "bps_inflation": "silver.inflasi_kota",
    "pihps_prices": "silver.harga_pangan",
    "wilayah_raw": "ref.ref_provinsi",
}


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def node_label(node_id: str, manifest: dict) -> str:
    if node_id in manifest.get("nodes", {}):
        node = manifest["nodes"][node_id]
        return f"{node.get('schema')}.{node.get('name')}"
    if node_id in manifest.get("sources", {}):
        source = manifest["sources"][node_id]
        return f"{source.get('schema')}.{source.get('name')}"
    return node_id


def safe_id(label: str) -> str:
    safe = "".join(char if char.isalnum() else "_" for char in label)
    return "n_" + safe.strip("_")


def model_nodes(manifest: dict) -> dict[str, dict]:
    return {
        node_id: node
        for node_id, node in manifest.get("nodes", {}).items()
        if node.get("resource_type") == "model"
    }


def seed_nodes(manifest: dict) -> dict[str, dict]:
    return {
        node_id: node
        for node_id, node in manifest.get("nodes", {}).items()
        if node.get("resource_type") == "seed"
    }


def gold_models(manifest: dict) -> list[tuple[str, dict]]:
    return sorted(
        (
            (node_id, node)
            for node_id, node in model_nodes(manifest).items()
            if node.get("schema") == "gold"
        ),
        key=lambda item: item[1].get("name", ""),
    )


def upstream_summary(node_id: str, manifest: dict) -> list[str]:
    parent_map = manifest.get("parent_map", {})
    upstream = []
    for parent_id in parent_map.get(node_id, []):
        upstream.append(node_label(parent_id, manifest))
    return sorted(upstream)


def generate_mermaid(manifest: dict) -> str:
    models = model_nodes(manifest)
    seeds = seed_nodes(manifest)
    sources = manifest.get("sources", {})
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()

    def add(label: str) -> str:
        node_id = safe_id(label)
        nodes[node_id] = label
        return node_id

    for external, bronze in EXTERNAL_TO_BRONZE.items():
        edges.add((add(f"external.{external}"), add(f"bronze.{bronze}")))
        canonical = BRONZE_TO_CANONICAL.get(bronze)
        if canonical:
            edges.add((add(f"bronze.{bronze}"), add(canonical)))

    for source_id in sources:
        add(node_label(source_id, manifest))

    for node_id, node in {**models, **seeds}.items():
        add(node_label(node_id, manifest))
        for parent_id in manifest.get("parent_map", {}).get(node_id, []):
            if parent_id in sources or parent_id in models or parent_id in seeds:
                edges.add(
                    (add(node_label(parent_id, manifest)), add(node_label(node_id, manifest)))
                )

    lines = ["```mermaid", "flowchart LR"]
    for node_id, label in sorted(nodes.items(), key=lambda item: item[1]):
        lines.append(f'    {node_id}["{label}"]')
    lines.append("")
    for left, right in sorted(edges):
        lines.append(f"    {left} --> {right}")
    lines.append("```")
    return "\n".join(lines)


def generate_markdown(manifest: dict) -> str:
    lines = [
        "# Data Lineage",
        "",
        "Generated from `dbt/panganwatch/target/manifest.json` plus manual external → bronze → canonical mappings.",
        "",
        "## External Sources → Bronze → Canonical Tables",
        "",
        "| External source | Bronze collection | Canonical table/model |",
        "|---|---|---|",
    ]
    for external, bronze in sorted(EXTERNAL_TO_BRONZE.items()):
        lines.append(f"| {external} | `bronze.{bronze}` | `{BRONZE_TO_CANONICAL[bronze]}` |")

    lines.extend(
        [
            "",
            "## dbt Sources",
            "",
            "| Source node | Relation | Description |",
            "|---|---|---|",
        ]
    )
    for source_id, source in sorted(manifest.get("sources", {}).items()):
        lines.append(
            f"| `{source_id}` | `{node_label(source_id, manifest)}` | {source.get('description', '')} |"
        )

    lines.extend(
        [
            "",
            "## Gold Model Upstream Summary",
            "",
            "| Gold model | Materialization | Direct upstream nodes |",
            "|---|---|---|",
        ]
    )
    for node_id, node in gold_models(manifest):
        upstream = upstream_summary(node_id, manifest)
        materialized = node.get("config", {}).get("materialized", "")
        lines.append(
            f"| `{node.get('schema')}.{node.get('name')}` | {materialized} | "
            f"{', '.join(f'`{item}`' for item in upstream)} |"
        )

    lines.extend(["", "## Diagram Alur Data", "", generate_mermaid(manifest), ""])
    return "\n".join(lines)


def main() -> None:
    manifest = load_manifest()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(generate_markdown(manifest), encoding="utf-8")
    print(f"Lineage documentation written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
