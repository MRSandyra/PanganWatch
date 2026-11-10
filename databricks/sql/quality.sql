-- Governance tables retain post-load results and error quarantine; warnings are never dropped.
CREATE TABLE IF NOT EXISTS ${PANGANWATCH_CATALOG}.pw_governance.pipeline_runs (
  run_id STRING, snapshot_id STRING, status STRING, started_at TIMESTAMP, completed_at TIMESTAMP,
  rows_processed BIGINT, rows_success BIGINT, rows_failed BIGINT, error_message STRING
) USING DELTA;
CREATE TABLE IF NOT EXISTS ${PANGANWATCH_CATALOG}.pw_governance.dq_results (
  run_id STRING, rule_id STRING, dataset STRING, column_name STRING, dimension STRING,
  severity STRING, rows_checked BIGINT, rows_failed BIGINT, pass_rate DECIMAL(5,2), checked_at TIMESTAMP
) USING DELTA;
CREATE TABLE IF NOT EXISTS ${PANGANWATCH_CATALOG}.pw_governance.quarantine (
  run_id STRING, dataset STRING, natural_key STRING, record STRING, rule_id STRING,
  reason STRING, quarantined_at TIMESTAMP, resolved_at TIMESTAMP, resolution_note STRING
) USING DELTA;
