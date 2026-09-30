#!/usr/bin/env bash
set -euo pipefail

# Simple init script for PanganWatch PostgreSQL
# Creates airflow database and governance schemas/tables

# Step 1: Create airflow database if it doesn't exist
if ! psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -tAc "SELECT 1 FROM pg_database WHERE datname='airflow'" | grep -q 1; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -c "CREATE DATABASE airflow;"
fi

# Step 2: Create schemas in main database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
create schema if not exists ref;
create schema if not exists silver;
create schema if not exists gold;
create schema if not exists governance;
create schema if not exists staging;
SQL

# Step 3: Create dbt_user role if not exists
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dbt_user') THEN
      CREATE ROLE dbt_user LOGIN PASSWORD '${POSTGRES_DBT_PASS:-dbt_dev_pass}';
   END IF;
END
$$;
SQL

# Step 4: Create governance tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS governance.pipeline_runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    source text NOT NULL,
    status text NOT NULL,
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    rows_processed int,
    rows_success int,
    rows_failed int,
    error_message text
);

CREATE TABLE IF NOT EXISTS governance.dq_results (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    rule_id text NOT NULL,
    dataset text NOT NULL,
    column_name text NOT NULL,
    dimension text NOT NULL,
    severity text NOT NULL,
    rows_checked int NOT NULL,
    rows_failed int NOT NULL,
    pass_rate numeric(5,2) NOT NULL,
    checked_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance.quarantine (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    dataset text NOT NULL,
    natural_key jsonb NOT NULL,
    record jsonb NOT NULL,
    rule_id text NOT NULL,
    reason text NOT NULL,
    quarantined_at timestamptz DEFAULT now(),
    resolved_at timestamptz,
    resolution_note text
);
SQL

# Step 5: Grant privileges
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
grant all privileges on schema ref to dbt_user;
grant all privileges on schema silver to dbt_user;
grant all privileges on schema gold to dbt_user;
grant all privileges on schema governance to dbt_user;
grant all privileges on schema staging to dbt_user;

grant all privileges on all tables in schema governance to dbt_user;
grant all privileges on all tables in schema silver to dbt_user;
grant all privileges on all tables in schema gold to dbt_user;
grant all privileges on all tables in schema ref to dbt_user;
SQL