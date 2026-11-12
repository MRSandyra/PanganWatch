# Implementation log

| Date | Status | Evidence |
|---|---|---|
| 2026-11-09 | implementation present / local tests NOT_EXECUTED | `databricks/src/`, scripts, tests, manual Lakeflow definition |
| 2026-11-09 | CLOUD_BLOCKED | no authenticated Free Edition workspace; see preflight |
| 2026-11-09 | NOT_EXECUTED | Bronze/Silver/Gold cloud runs, SQL warehouse, Lakeflow and dashboard |

| 2026-11-11 | PASSED | Databricks Free Edition preflight, reference dimensions, WFP and Open-Meteo Bronze/Silver, DQ, Gold, and source-replay reconciliation; see `evidence/cloud-run-20261111.md` |
| 2026-11-11 | PASSED | Manual `panganwatch_batch` job run completed: nine tasks successful in 2m42s; source replay passed for price and weather |
| 2026-11-11 | PASSED | Published dashboard with four pages: price trend, data quality, provincial disparity, and monthly rainfall |
| 2026-11-11 | NOT_EXECUTED | Row-level parity against the pre-migration local/legacy database |
| 2026-11-12 | FAILED | Recovered legacy PostgreSQL overlap compared against cloud Silver: 155 legacy-only price keys; weather keys match but 40,086 daily values differ. Inputs are not proven byte-identical; see `evidence/legacy-overlap-20261112.md` |
| 2026-11-12 | PASSED | Recovered Mongo Bronze raw payloads replayed to isolated `pw_legacy_replay`: 20,864 price and 17,936 weather records matched the restored legacy database exactly; see `evidence/legacy-raw-replay-20261112.md` |

The historical `CLOUD_BLOCKED` entries describe the state before workspace
access was available. They are superseded by the 2026-11-11 evidence above;
The prior `NOT_EXECUTED` and bounded-overlap failure are superseded for parity
purposes by the successful raw replay. They remain in the log as lineage of the
investigation.
