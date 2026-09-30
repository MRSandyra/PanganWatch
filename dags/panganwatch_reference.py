"""F7: manual DAG — dbt seed + reference-data validation (F2/F3a)."""

from __future__ import annotations

from datetime import timedelta

import pendulum
from _common import run_dbt, write_failure_to_governance
from airflow.decorators import dag, task

DEFAULT_ARGS = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": write_failure_to_governance,
}

EXPECTED_COUNTS = {
    "ref.ref_provinsi": 38,
    "ref.ref_kabkota": 513,
    "ref.ref_crosswalk_wilayah": 2565,
    "ref.ref_komoditas": 14,
    "ref.ref_komoditas_alias": 69,
    "ref.ref_provinsi_alias": 34,
}


@dag(
    dag_id="panganwatch_reference",
    schedule=None,  # manual trigger only
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Jakarta"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["panganwatch", "reference"],
)
def panganwatch_reference():
    @task
    def dbt_seed():
        run_dbt("seed")

    @task
    def validate_reference():
        from panganwatch.db import get_postgres_connection

        conn = get_postgres_connection()
        errors = []
        try:
            with conn.cursor() as cur:
                for table, expected in EXPECTED_COUNTS.items():
                    cur.execute(f"SELECT count(*) FROM {table}")
                    actual = cur.fetchone()[0]
                    print(f"{table}: {actual} (expected {expected})")
                    if actual != expected:
                        errors.append(f"{table}: got {actual}, expected {expected}")
        finally:
            conn.close()
        if errors:
            raise RuntimeError("Reference validation failed: " + "; ".join(errors))

    dbt_seed() >> validate_reference()


panganwatch_reference()
