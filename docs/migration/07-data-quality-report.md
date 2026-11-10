# Data quality migration report

All 27 source rule IDs map one-to-one in `databricks/config/quality_mapping.yml`; the automated test fails if either catalog changes without a matching migration entry. The implemented semantics retain post-load outcomes: `error` failures are recorded and block Gold; `warn` failures remain published in governance and never remove records.

Priority mappings include `HP-012` / `HP-014` province coverage warnings and `CH-007` `tmin_c <= tmax_c` error check. Reference, freshness, aggregate and cross-source checks require a real Spark/warehouse run against a snapshot and are NOT_EXECUTED in cloud.
