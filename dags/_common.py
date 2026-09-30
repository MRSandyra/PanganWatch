"""Shared helpers for PanganWatch DAGs. Not a DAG itself (no top-level DAG
object), so Airflow's DAG file processor imports it without complaint.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

DBT_PROJECT_DIR = Path("/opt/airflow/dbt/panganwatch")
# Single source of truth: DBT_BIN is set by docker/airflow/Dockerfile (DEC-033)
# so the DAG and any ad-hoc `docker compose exec airflow ...` shell command
# agree on the same path without duplicating the literal string. /home/airflow,
# not /opt/dbt-venv: /opt is not writable by the non-root airflow UID in the
# official image (DEC-030). The fallback below only matters when this module
# is imported outside the container (e.g. tests).
DBT_BIN = os.environ.get("DBT_BIN", "/home/airflow/dbt-venv/bin/dbt")


def write_failure_to_governance(context: dict) -> None:
    """on_failure_callback: log a 'failed' row to governance.pipeline_runs,
    without any external notification (F7)."""
    from panganwatch.db import get_postgres_connection

    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    exception = context.get("exception")
    run_id = str(uuid.uuid4())

    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO governance.pipeline_runs
                   (run_id, source, status, completed_at, rows_processed, rows_success, rows_failed, error_message)
                   VALUES (%s, %s, 'failed', now(), 0, 0, 0, %s)""",
                (run_id, f"airflow:{dag_id}.{task_id}", str(exception)[:2000]),
            )
        conn.commit()
    finally:
        conn.close()


def run_dbt(*args: str, timeout: int = 600) -> None:
    """Run a dbt command in the dedicated dbt venv (AD-13). Raises on failure."""
    cmd = [DBT_BIN, *args, "--profiles-dir", str(DBT_PROJECT_DIR)]
    result = subprocess.run(
        cmd, cwd=DBT_PROJECT_DIR, capture_output=True, text=True, timeout=timeout
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"dbt {' '.join(args)} failed (exit {result.returncode})")
