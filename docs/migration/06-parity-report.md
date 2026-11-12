# Parity report

**Status:** PASSED. Recovered legacy Mongo Bronze payloads were reconstructed
into immutable snapshots and replayed to `workspace.pw_legacy_replay` without
changing production tables. Exact comparison against restored legacy PostgreSQL
returned zero missing keys and zero value mismatches for 20,864 price and
17,936 weather records. See
[`evidence/legacy-raw-replay-20261112.md`](evidence/legacy-raw-replay-20261112.md).

The earlier bounded comparison against newer production snapshots failed (155
legacy-only price keys and weather value drift) because it did not use identical
inputs. It remains recorded in
[`evidence/legacy-overlap-20261112.md`](evidence/legacy-overlap-20261112.md)
as a provenance finding, not as the authoritative parity result.

Use `scripts/compare_local_cloud.py` with same-grain JSON/JSONL extracts. Counts, keys, dates and categories must match exactly; decimal values use source-defined precision, and floating statistical values must use documented tolerances. Any result is emitted with dataset/key/field/local/cloud/difference/classification/investigation status. Historical README metrics must not be compared to refreshed API data.
