"""F7: daily DAG — ingest_harga -> ingest_cuaca_harian -> dq_check -> dbt_build -> export_bi -> build_report.

export_bi/build_report are skipped with an explicit reason: they run outside
Airflow via `make export`/`make report` instead. They are never faked as
'success'.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pendulum
from _common import run_dbt, write_failure_to_governance
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException

DEFAULT_ARGS = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": write_failure_to_governance,
}


@dag(
    dag_id="panganwatch_daily",
    schedule="0 10 * * *",  # 10:00 WIB daily
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Jakarta"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["panganwatch"],
)
def panganwatch_daily():
    @task
    def ingest_harga():
        from panganwatch.sources import hdx_wfp

        rc = hdx_wfp.main(["--backfill"])
        if rc != 0:
            raise RuntimeError(f"hdx_wfp ingestion failed, exit={rc}")

    @task
    def ingest_cuaca_harian():
        from panganwatch.sources import open_meteo

        rc = open_meteo.main(["--backfill"])
        if rc != 0:
            raise RuntimeError(f"open_meteo ingestion failed, exit={rc}")

    @task
    def dq_check():
        """Run the DQEngine against the current silver data (a real check, not a stub).

        F4's DQEngine.check_records() is designed to run before an upsert; here
        it is used as a periodic DQ gate over data already in silver, writing
        real results to governance.dq_results (which feeds gold.mart_dq_scorecard, F5).
        """
        from psycopg.rows import dict_row

        from panganwatch.db import get_postgres_connection
        from panganwatch.dq.engine import DQEngine

        run_id = str(uuid.uuid4())
        engine = DQEngine()
        conn = get_postgres_connection()
        try:
            for dataset, table in [
                ("silver.harga_pangan", "silver.harga_pangan"),
                ("silver.cuaca_harian", "silver.cuaca_harian"),
                ("silver.inflasi_kota", "silver.inflasi_kota"),
            ]:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(f"SELECT * FROM {table}")
                    records = cur.fetchall()
                clean, quarantined = engine.check_records(dataset, records, run_id)
                print(f"{dataset}: {len(clean)} clean, {len(quarantined)} quarantined")
        finally:
            conn.close()

    @task
    def dbt_build():
        run_dbt("build", "--exclude", "resource_type:seed")

    @task
    def export_bi():
        raise AirflowSkipException(
            "export_bi is run outside Airflow via `make export` (analytics.export_bi) — DEC-029"
        )

    @task
    def build_report():
        raise AirflowSkipException(
            "build_report is run outside Airflow via `make report` (analytics.report) — DEC-029"
        )

    (
        ingest_harga()
        >> ingest_cuaca_harian()
        >> dq_check()
        >> dbt_build()
        >> export_bi()
        >> build_report()
    )


panganwatch_daily()
