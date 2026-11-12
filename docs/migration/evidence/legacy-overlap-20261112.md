# Legacy-to-cloud overlap comparison — 2026-11-12

This is an actual comparison of a recovered legacy PostgreSQL backup against
Databricks Silver extracts. It is a bounded overlap test, not a full-history
parity result: the legacy and cloud source snapshots are not demonstrably
byte-identical.

| Field | Value |
|---|---|
| test_name | Legacy PostgreSQL versus Databricks Silver overlap comparison |
| execution time | 2026-11-12, Asia/Bangkok |
| legacy database | `panganwatch_legacy_compare` (restored separately; active `panganwatch` was not modified) |
| legacy backup SHA-256 | `CB7944C8C8256D98CBCBEBA66A4E90DC2C60A649F50187EDDFFAB640F2EA49D9` |
| cloud environment | Databricks Free Edition (workspace identifier redacted) |
| overlap | 2025-06-15 through 2026-06-15 |
| comparison rule | Exact business key and field equality; source labels were canonically renamed only (`HDX WFP` → `hdx_wfp`, `Open-Meteo Archive` → `open_meteo_archive_era5`) |
| overall status | FAILED — source snapshots are not identical; do not claim legacy parity |

## Price (`silver.harga_pangan`)

| Result | Count |
|---|---:|
| Legacy records | 20,864 |
| Cloud records | 20,709 |
| Exact common business keys with no value mismatch | 20,709 |
| Legacy-only business keys | 155 |
| Cloud-only business keys | 0 |
| Value mismatches for common keys | 0 |

The 155 missing cloud keys occur in every month of the overlap and span 27
provinces and seven commodity IDs. They are individual market observations;
examples include `Pasar Nauli Sibolga`, `Pasar Kramatjati`, and `Pasar Mundu`.
Because every common key has identical values, this is evidence of source-row
availability drift rather than a detected value transformation error.

## Weather (`silver.cuaca_harian`)

| Result | Count |
|---|---:|
| Legacy records | 13,908 |
| Cloud records | 13,908 |
| Missing business keys on either side | 0 |
| Compared value fields | 41,724 |
| Equal value fields | 1,638 |
| Value mismatches | 40,086 |
| Precipitation mismatches | 13,079 |
| Maximum-temperature mismatches | 13,523 |
| Minimum-temperature mismatches | 13,484 |

The date/province key coverage matches exactly, but most daily observations do
not. The recovered database does not prove which archived Open-Meteo model
version, coordinate treatment, or historical response was used at its original
load time. Treat the difference as **source-snapshot drift under
investigation**, not as a transform pass or a causal data-quality conclusion.

## Required next step for full legacy parity

Recover the original Bronze/raw payloads from the old device's
`panganwatch-mongo` volume, freeze them with manifests, and use those immutable
inputs for both legacy replay and a dedicated cloud replay. Until then, the
migration remains `CLOUD_PARTIAL`.
