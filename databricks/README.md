# PanganWatch Databricks Free Edition migration

This directory adds a **batch-only** Databricks Lakehouse implementation beside the retained local MongoDB, PostgreSQL, Airflow, dbt, and Kafka system. It is configured entirely through `PANGANWATCH_CATALOG`; no workspace URL, token, or paid storage is committed.

## Status

`PORTFOLIO_READY` as of 2026-11-12. The Databricks Free Edition workspace,
reference data, both Bronze/Silver paths, DQ, Gold marts, source-replay
reconciliation, the nine-task `panganwatch_batch` job, and the published
dashboard were observed successfully. The migration suite also passes locally:
`uv run pytest -q databricks/tests` reports 25 passed.

The recovered legacy raw Bronze payloads were replayed into isolated tables
with zero missing keys and zero value mismatches against the restored legacy
PostgreSQL state. Production tables and the published dashboard were not
modified. See
[`../docs/migration/10-final-verification.md`](../docs/migration/10-final-verification.md)
and the sanitized
[`../docs/migration/evidence/legacy-raw-replay-20261112.md`](../docs/migration/evidence/legacy-raw-replay-20261112.md).

## Local validation and cloud reruns

1. Freeze an allowed source file: `uv run python scripts/export_frozen_snapshot.py <file> --source-name hdx_wfp --source-url <actual-url> --license CC-BY-IGO --destination <directory>`.
2. Validate it before upload: `uv run python scripts/prepare_databricks_upload.py <file> <manifest> --catalog workspace`.
3. Run `uv run pytest -q databricks/tests` and `git diff --check`.
4. Upload the exact validated snapshot and manifest to the existing Unity
   Catalog Volume, then run the configured `panganwatch_batch` job. Use the
   matching snapshot paths as job parameters; do not point a rerun at a live,
   refreshed API response.

The notebooks are intentionally thin. Reusable source, Silver, DQ, Gold, and
reconciliation functions live in `src/`; `pyspark`/`delta-spark` are only
required in Databricks, not in the original local runtime. Detailed click-by-
click owner actions live in [`../docs/migration/owner-actions.md`](../docs/migration/owner-actions.md).
