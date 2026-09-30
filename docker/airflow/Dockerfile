FROM apache/airflow:2.9.0-python3.11

WORKDIR /opt/airflow

# Install build dependencies first
RUN pip install hatchling editables

# Copy source files (owned by airflow user UID 50000)
COPY --chown=50000:50000 pyproject.toml uv.lock ./
COPY --chown=50000:50000 src/ ./src/
COPY --chown=50000:50000 dags/ ./dags/
COPY --chown=50000:50000 dbt/ ./dbt/
COPY --chown=50000:50000 config/ ./config/
COPY --chown=50000:50000 scripts/ ./scripts/

# Install panganwatch itself with --no-deps, then only the runtime libraries
# the DAG task code actually imports (httpx, pydantic(-settings), pyyaml,
# psycopg, pymongo). This is deliberately NOT the same set as pyproject.toml's
# full `dependencies` list: dbt-core/dbt-postgres run in their own venv
# (AD-13, below) and are never imported from Airflow's own environment, and
# pulling them (or the official Airflow constraints file) into this
# environment breaks Airflow's own package versions (DEC-030 documents 3
# approaches tried). `pip check` is run for visibility (its output is
# evidence, not a hard gate — see DEC-030 for why a fully clean `pip check`
# is not achievable, or meaningful, for a customized apache/airflow image).
# The real, load-bearing checks are: `airflow version` unchanged, and Airflow
# actually starting + DAGs parsing (verified separately via `verify_phase_7`,
# see CHANGELOG.md).
RUN pip install -e . --no-build-isolation --no-deps \
    && pip install "httpx>=0.27.0" tenacity pydantic pydantic-settings pyyaml "psycopg[binary]" pymongo \
    && (pip check || true) \
    && airflow version | grep -qx 2.9.0

# dbt in a separate venv (AD-13) so its dependency set never conflicts with
# Airflow's. /opt is not writable by the non-root airflow UID (50000) in the
# official image, so the venv lives under /home/airflow instead (DEC-030).
RUN python -m venv /home/airflow/dbt-venv && \
    /home/airflow/dbt-venv/bin/pip install dbt-core dbt-postgres

# Single source of truth for the dbt binary path (DEC-033): DBT_BIN is read
# by dags/_common.py, and PATH is extended so a bare `dbt` also works for any
# ad-hoc `docker compose exec airflow dbt ...` (previously "executable file
# not found in $PATH" because dbt-venv/bin was never on PATH and the path was
# hardcoded, inconsistently, in more than one place).
ENV DBT_BIN=/home/airflow/dbt-venv/bin/dbt
ENV PATH="/home/airflow/dbt-venv/bin:${PATH}"

ENV AIRFLOW__CORE__LOAD_EXAMPLES=False

RUN mkdir -p /opt/airflow/logs /opt/airflow/plugins

EXPOSE 8080

CMD ["airflow", "standalone"]
