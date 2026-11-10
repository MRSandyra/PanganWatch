# PanganWatch Databricks Free Edition migration

This directory adds a **batch-only** Databricks Lakehouse implementation beside the retained local MongoDB, PostgreSQL, Airflow, dbt, and Kafka system. It is configured entirely through `PANGANWATCH_CATALOG`; no workspace URL, token, or paid storage is committed.

## Status

`CLOUD_BLOCKED`. No authenticated Databricks Free Edition workspace was available during this change, so every cloud capability remains `NOT_EXECUTED`; see [`../docs/migration/01-workspace-preflight.md`](../docs/migration/01-workspace-preflight.md). The local implementation is present, but its pytest suite remains `NOT_EXECUTED` because this environment cannot resolve required packages.

## Offline workflow

1. Freeze an existing allowed source file: `python scripts/generate_snapshot_manifest.py <file> --source-name hdx_wfp --source-url <actual-url> --license CC-BY-IGO`.
2. Validate it before upload: `python scripts/prepare_databricks_upload.py <file> <manifest>`.
3. Run `python -m pytest databricks/tests -q`.
4. After a successful Free Edition preflight, upload the exact validated file to the indicated Unity Catalog Volume, configure the manual Lakeflow job, and run notebooks in numerical order.

The notebooks are intentionally thin. Reusable source, Silver, DQ, Gold, and reconciliation functions live in `src/`; `pyspark`/`delta-spark` are only required in Databricks, not in the original local runtime.
