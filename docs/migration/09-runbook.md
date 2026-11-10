# Lakeflow operations runbook

1. Complete preflight and set `PANGANWATCH_CATALOG`.
2. Create a manifest and validate a snapshot locally; never overwrite an existing immutable snapshot.
3. Upload the exact file and manifest to `/Volumes/<catalog>/pw_landing/snapshots/`.
4. Configure `databricks/jobs/panganwatch_batch.yml` as a manual-only sequential job.
5. Run: validate snapshot → Bronze → Silver → DQ → Gold → reconcile.
6. Stop publication on any `error` DQ result. Correct input in a new snapshot; rerun safely with its new run ID.
7. Record evidence in `evidence/` using test name, UTC time, environment, redacted workspace, snapshot, command/query, run ID, expected/actual, status, and sanitized error.

Cleanup is manual and must target only `pw_*` resources after retention review. Do not delete legacy Docker volumes or unrelated workspace objects.
