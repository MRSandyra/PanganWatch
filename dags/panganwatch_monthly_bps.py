"""F7/F3b: monthly DAG — ingest_bps -> dbt_build_bps.

ingest_bps calls the BPS WebAPI (city IHK/inflation, DEC-039) when
BPS_API_KEY is set. Only when the key is empty does this task log a
'skipped' row in governance.pipeline_runs and raise an AirflowSkipException
(dbt_build_bps is skipped too) -- it is never faked as a success.
dbt_build_bps reseeds the city mapping (ref_ihk_kota) and then builds
stg_inflasi_kota and mart_inflasi_vs_harga.
"""

from __future__ import annotations

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
    dag_id="panganwatch_monthly_bps",
    schedule="@monthly",
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Jakarta"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["panganwatch", "bps"],
)
def panganwatch_monthly_bps():
    @task
    def ingest_bps():
        from panganwatch.sources import bps

        if bps.api_key_status() == "EMPTY":
            rc = bps.main(["--run"])  # records a 'skipped' governance.pipeline_runs row
            raise AirflowSkipException(
                f"BPS_API_KEY is empty; ingest_bps is skipped (bps.main exit={rc})"
            )
        rc = bps.main(["--run"])
        if rc != 0:
            raise RuntimeError(f"BPS ingestion failed, exit={rc}")

    @task
    def dbt_build_bps():
        run_dbt("seed", "--select", "ref_ihk_kota")
        run_dbt("build", "--select", "stg_inflasi_kota", "mart_inflasi_vs_harga")

    ingest_bps() >> dbt_build_bps()


panganwatch_monthly_bps()
