"""Generate the deterministic governance policy documents."""

from pathlib import Path

RETENTION_PATH = Path("docs/governance/retention_policy.md")
DAMA_PATH = Path("docs/governance/dama_mapping.md")


def retention_markdown() -> str:
    return """# Retention Policy

PanganWatch's retention policy. Each row states the technical control and how to verify it.

| Zone/artifact | Retention | Technical mechanism | How to verify |
|---|---|---|---|
| Bronze MongoDB (`hdx_wfp_prices`, `open_meteo_daily`, `open_meteo_current`, `pihps_prices`, `bps_inflation`, `wilayah_raw`) | 90 days | TTL index on `_meta.fetched_at`, `expireAfterSeconds=7776000`, created by `src/panganwatch/bronze.py` | `docker compose exec mongo mongosh --quiet --eval 'db.getSiblingDB("bronze").hdx_wfp_prices.getIndexes()'` and check for TTL 7776000 |
| Governance quarantine with `resolved_at` set | 180 days after resolution | The `panganwatch_retention` DAG deletes rows with the specific predicate `resolved_at < NOW() - INTERVAL '180 days'` | Query the count with the same predicate before maintenance; re-querying must return 0 old rows |
| Governance `pipeline_runs`, `dq_results`, unresolved quarantine, weather alerts | Permanent | No deletion task; append-only/history policy | `SELECT count(*) FROM governance.<table>` and the run-log audit |
| Silver (`harga_pangan`, `cuaca_harian`, `cuaca_terkini`) | Permanent | No purge job; upsert only prevents natural-key duplicates | Query `MIN/MAX` date and the table row count |
| Gold dbt (`dim_*`, `fct_harga_bulanan`, `mart_*`) | Permanent | dbt models are rebuilt/incremental per config, with no retention delete | `dbt build --exclude resource_type:seed` then a row count per model |
| Kafka `weather.current.raw`, `weather.current.dlq`, `weather.alert` | 7 days | Topic config `retention.ms=604800000`, created by `docker/kafka/init_topics.sh` | `kafka-topics.sh --describe --topic <topic>` and check for `retention.ms=604800000` |

## Safety constraints

- No `TRUNCATE`, `DROP`, or `DELETE` without a `WHERE` clause.
- A legitimate DELETE/UPDATE must be preceded by a `SELECT count(*)` with an identical predicate.
- `governance.quarantine` and `governance.dq_results` rows are never deleted to clear old DQ
  results; fixing a rule produces a new run history instead.
"""


def dama_markdown() -> str:
    rows = [
        (
            "Data Governance",
            "Covered",
            "governance_raci.csv; governance_glossary.csv; config/dq_rules.yml; docs/governance/retention_policy.md; incident_log.md",
        ),
        (
            "Data Architecture",
            "Covered",
            "docker-compose.yml; src/panganwatch/bronze.py; dbt/panganwatch/dbt_project.yml; docs/architecture.md where available",
        ),
        (
            "Data Modeling & Design",
            "Covered",
            "dbt/panganwatch/models/; contracts/; docs/data_dictionary.md",
        ),
        (
            "Data Storage & Operations",
            "Covered",
            "docker-compose.yml; sql/ddl/init_governance.sql; src/panganwatch/db.py; retention_policy.md",
        ),
        (
            "Data Security",
            "Partial",
            ".env.example; .gitignore; local secret management. Encryption at rest/transit, production RBAC, and network policy are not covered — out of scope for a local portfolio project.",
        ),
        (
            "Data Integration & Interoperability",
            "Covered",
            "src/panganwatch/sources/; src/panganwatch/stream/; contracts/; bronze envelope",
        ),
        (
            "Metadata Management",
            "Covered",
            "src/panganwatch/governance/lineage.py; data_dictionary.py; glossary.py; raci.py; docs/lineage.md",
        ),
        (
            "Data Quality",
            "Covered",
            "config/dq_rules.yml; src/panganwatch/dq/; governance.dq_results; governance.quarantine; docs/governance/dq_rules.md",
        ),
        (
            "Reference & Master Data",
            "Covered",
            "dbt/panganwatch/seeds/ref_*.csv; docs/governance/crosswalk_report.md",
        ),
        (
            "Data Warehousing & BI",
            "Covered",
            "dbt/panganwatch/models/; manifest.json; catalog.json; mart_dq_scorecard",
        ),
        (
            "Document & Content Management",
            "Not covered",
            "No CMS/DMS; this repository manages pipeline artifacts and technical documentation, not enterprise content.",
        ),
    ]
    lines = [
        "# DAMA-DMBOK Knowledge Area Mapping",
        "",
        "An honest mapping of the 11 DAMA-DMBOK knowledge areas to PanganWatch artifacts.",
        "",
        "| Knowledge area | Coverage | Concrete artifacts / limitations |",
        "|---|---|---|",
    ]
    lines.extend(f"| {area} | {status} | {artifact} |" for area, status, artifact in rows)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "10 areas are covered or partially covered; Document & Content Management is not covered because it is not a goal of this system. Data Security is only a local-development baseline, not production hardening.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    RETENTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    RETENTION_PATH.write_text(retention_markdown(), encoding="utf-8")
    DAMA_PATH.write_text(dama_markdown(), encoding="utf-8")
    print(f"Policy documents written to {RETENTION_PATH} and {DAMA_PATH}")


if __name__ == "__main__":
    main()
