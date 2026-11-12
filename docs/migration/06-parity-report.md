# Parity report

**Status:** FAILED for the executed bounded overlap comparison. A recovered
legacy PostgreSQL backup was compared with Databricks Silver extracts over
2025-06-15 through 2026-06-15. Price has 20,709 exact common keys and 155
legacy-only keys; weather has identical date/province coverage (13,908 keys)
but 40,086 value mismatches across 41,724 compared fields. The source snapshots
are not proven identical, so this does not establish legacy parity. See
[`evidence/legacy-overlap-20261112.md`](evidence/legacy-overlap-20261112.md).

Use `scripts/compare_local_cloud.py` with same-grain JSON/JSONL extracts. Counts, keys, dates and categories must match exactly; decimal values use source-defined precision, and floating statistical values must use documented tolerances. Any result is emitted with dataset/key/field/local/cloud/difference/classification/investigation status. Historical README metrics must not be compared to refreshed API data.
