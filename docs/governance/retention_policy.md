# Retention Policy

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
