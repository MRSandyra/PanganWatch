# Parity report

**Status:** NOT_EXECUTED. No identical frozen input is available yet, so there is no valid local-vs-cloud result.

Use `scripts/compare_local_cloud.py` with same-grain JSON/JSONL extracts. Counts, keys, dates and categories must match exactly; decimal values use source-defined precision, and floating statistical values must use documented tolerances. Any result is emitted with dataset/key/field/local/cloud/difference/classification/investigation status. Historical README metrics must not be compared to refreshed API data.
