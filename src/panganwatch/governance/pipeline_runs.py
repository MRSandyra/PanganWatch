"""Shared governance.pipeline_runs logging for ingestion jobs.

governance.pipeline_runs columns (from F1 DDL) map to the original run-log
spec as: rows_processed=rows_fetched, rows_success=rows_loaded,
rows_failed=rows_quarantined.
"""

from __future__ import annotations

from panganwatch.db import get_postgres_connection


def start_run(run_id: str, source: str) -> None:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO governance.pipeline_runs (run_id, source, status)
                   VALUES (%s, %s, 'running')""",
                (run_id, source),
            )
        conn.commit()
    finally:
        conn.close()


def finish_run(
    run_id: str,
    source: str,
    status: str,
    rows_fetched: int = 0,
    rows_loaded: int = 0,
    rows_quarantined: int = 0,
    error_message: str | None = None,
) -> None:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE governance.pipeline_runs
                   SET status = %s, completed_at = now(),
                       rows_processed = %s, rows_success = %s, rows_failed = %s,
                       error_message = %s
                   WHERE run_id = %s AND source = %s""",
                (
                    status,
                    rows_fetched,
                    rows_loaded,
                    rows_quarantined,
                    error_message,
                    run_id,
                    source,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def skip_run(run_id: str, source: str, reason: str) -> None:
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO governance.pipeline_runs
                   (run_id, source, status, completed_at, rows_processed, rows_success, rows_failed, error_message)
                   VALUES (%s, %s, 'skipped', now(), 0, 0, 0, %s)""",
                (run_id, source, reason),
            )
        conn.commit()
    finally:
        conn.close()
