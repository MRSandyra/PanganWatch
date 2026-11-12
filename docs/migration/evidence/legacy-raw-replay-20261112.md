# Legacy raw replay evidence — 2026-11-12

The recovered PostgreSQL database and MongoDB Bronze payloads were used to
reconstruct two immutable snapshots. Databricks replayed those snapshots into
an isolated schema; no production Bronze, Silver, Gold, or dashboard table was
modified.

| Field | Value |
|---|---|
| test_name | Legacy raw Bronze replay and exact Silver comparison |
| execution time | 2026-11-12, Asia/Bangkok |
| legacy PostgreSQL backup SHA-256 | `CB7944C8C8256D98CBCBEBA66A4E90DC2C60A649F50187EDDFFAB640F2EA49D9` |
| WFP Mongo export SHA-256 | `820C05043F320809BCAC21B4D7170E1C7B149E331F0A371F43FBBEEBB7F347AA` |
| Open-Meteo Mongo export SHA-256 | `431F0E099B9445802AF0616A1C3CB9DDD65B43FFB4ABD6B1206EB1A586B3D45C` |
| cloud environment | Databricks Free Edition (workspace identifier redacted) |
| replay schema | `workspace.pw_legacy_replay` |
| production_tables_modified | `False` |
| overall status | PASSED |

## Reconstructed snapshots

| Dataset | Snapshot ID | Reconstruction | Replay table |
|---|---|---|---|
| WFP price | `c18096c2efb18b504a131abe` | 26 raw Mongo documents replayed in `fetched_at` order; 20,864 source-native rows | `workspace.pw_legacy_replay.harga_pangan` |
| Open-Meteo weather | `f8a02eba412061d613bc7487` | 11 raw Mongo documents replayed in `fetched_at` order; 17,936 daily records | `workspace.pw_legacy_replay.cuaca_harian` |

Both snapshots passed local manifest/checksum validation before upload. The
Databricks replay notebook reported `production_tables_modified: False`.

## Exact result

| Dataset | Legacy records | Replay records | Comparison result |
|---|---:|---:|---|
| `harga_pangan` | 20,864 | 20,864 | PASS; 0 missing keys and 0 value mismatches |
| `cuaca_harian` | 17,936 | 17,936 | PASS; 0 missing keys and 0 value mismatches |

The earlier bounded comparison against newer production snapshots remains a
valid historical finding: it showed why source snapshots must be frozen. This
raw replay is the authoritative legacy-parity result because it uses recovered
source-native Bronze payloads that generated the legacy state.
