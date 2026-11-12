# Cloud evidence index

Actual sanitized evidence is available in
[cloud-run-20261111.md](cloud-run-20261111.md). It records the successful
Databricks Free Edition run and published dashboard without exposing a workspace
host, URL, or user identity.

For each future actual operation, add a sanitized JSON or Markdown record with:

`test_name`, `execution_time_utc`, `environment`, `workspace_identifier_redacted`, `snapshot_id`, `command_or_query`, `run_id_if_available`, `expected_result`, `actual_result`, `status`, and `error_if_any`.

Permitted statuses are `PASSED`, `FAILED`, `NOT_EXECUTED`, and `BLOCKED_BY_PLATFORM`. Do not create placeholder screenshots or mark generated notebooks as executed.
