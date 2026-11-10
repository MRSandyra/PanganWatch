# Cloud evidence index

No cloud evidence has been collected. For each actual operation, add a sanitized JSON or Markdown record with:

`test_name`, `execution_time_utc`, `environment`, `workspace_identifier_redacted`, `snapshot_id`, `command_or_query`, `run_id_if_available`, `expected_result`, `actual_result`, `status`, and `error_if_any`.

Permitted statuses are `PASSED`, `FAILED`, `NOT_EXECUTED`, and `BLOCKED_BY_PLATFORM`. Do not create placeholder screenshots or mark generated notebooks as executed.
