"""F7: weekly DAG — quarantine retention + Mongo TTL index verification (AD-04)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pendulum
from _common import write_failure_to_governance
from airflow.decorators import dag, task

DEFAULT_ARGS = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": write_failure_to_governance,
}

BRONZE_COLLECTIONS = ["hdx_wfp_prices", "open_meteo_daily", "open_meteo_current"]


@dag(
    dag_id="panganwatch_retention",
    schedule="@weekly",
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Jakarta"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["panganwatch", "retention"],
)
def panganwatch_retention():
    @task
    def cleanup_quarantine():
        """Delete resolved quarantine rows older than 180 days (AD-04)."""
        from panganwatch.db import get_postgres_connection

        conn = get_postgres_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM governance.quarantine
                       WHERE resolved_at IS NOT NULL
                         AND resolved_at < now() - interval '180 days'"""
                )
                deleted = cur.rowcount
            conn.commit()
        finally:
            conn.close()
        print(f"Deleted {deleted} resolved quarantine rows older than 180 days")
        return deleted

    @task
    def verify_ttl_indexes():
        """Confirm the TTL index (AD-04, 7776000 seconds = 90 days) still exists on
        every bronze collection managed by bronze.store_raw()."""
        from panganwatch.db import get_mongo_client

        client = get_mongo_client()
        try:
            db = client.get_database()
            missing = []
            for coll_name in BRONZE_COLLECTIONS:
                indexes = db[coll_name].index_information()
                has_ttl = any(idx.get("expireAfterSeconds") == 7776000 for idx in indexes.values())
                print(f"{coll_name}: 90-day TTL {'PRESENT' if has_ttl else 'MISSING'}")
                if not has_ttl:
                    missing.append(coll_name)
        finally:
            client.close()
        if missing:
            raise RuntimeError(f"TTL index missing on collections: {missing}")

    @task
    def write_summary(deleted_count: int):
        from panganwatch.governance.pipeline_runs import finish_run, start_run

        run_id = str(uuid.uuid4())
        start_run(run_id, "retention")
        finish_run(
            run_id,
            "retention",
            "success",
            rows_fetched=0,
            rows_loaded=0,
            rows_quarantined=deleted_count,
        )
        print(f"Retention summary written: run_id={run_id}, deleted={deleted_count}")

    deleted = cleanup_quarantine()
    deleted >> verify_ttl_indexes() >> write_summary(deleted)


panganwatch_retention()
