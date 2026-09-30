#!/usr/bin/env python3
"""PanganWatch database helpers.

Real PostgreSQL and MongoDB connections, governance schema initialization,
and F1 verification hooks. Credentials come from environment variables only.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import psycopg
except ImportError:  # pragma: no cover - unit tests can run without extras
    psycopg = None  # type: ignore[assignment]

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover - unit tests can run without extras
    MongoClient = Any  # type: ignore[assignment,misc]

DB_DIR = Path(__file__).resolve().parents[2]
load_dotenv(DB_DIR / ".env", override=True)
DDL_PATH = DB_DIR / "sql" / "ddl" / "init_governance.sql"


def get_env_var(name: str, default: str | None = None) -> str | None:
    """Read an environment variable for database configuration."""
    return os.getenv(name, default)


def get_postgres_connection() -> Any:
    """Return a psycopg connection using environment variables."""
    if psycopg is None:
        raise RuntimeError("psycopg is not installed")
    return psycopg.connect(
        host=get_env_var("POSTGRES_HOST", "localhost") or "localhost",
        port=int(get_env_var("POSTGRES_PORT", "5432") or "5432"),
        dbname=get_env_var("POSTGRES_DB", "panganwatch") or "panganwatch",
        user=get_env_var("POSTGRES_USER", "postgres") or "postgres",
        password=get_env_var("POSTGRES_PASSWORD", ""),
        connect_timeout=int(get_env_var("POSTGRES_CONNECT_TIMEOUT", "5") or "5"),
    )


def get_mongo_client() -> Any:
    """Return a pymongo MongoClient using environment variables."""
    if MongoClient is Any:
        raise RuntimeError("pymongo is not installed")
    return MongoClient(
        get_env_var("MONGO_URI", "mongodb://localhost:27017") or "mongodb://localhost:27017",
        serverSelectionTimeoutMS=int(get_env_var("MONGO_SERVER_TIMEOUT_MS", "5000") or "5000"),
    )


def read_governance_ddl() -> str:
    """Read governance DDL from the repository."""
    return DDL_PATH.read_text(encoding="utf-8")


def apply_governance_ddl(conn: Any) -> None:
    """Apply governance DDL idempotently."""
    ddl = read_governance_ddl()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def ensure_governance_schema(conn: Any) -> None:
    """Ensure governance schema and tables exist."""
    ddl = read_governance_ddl()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _docker_ps_json() -> str:
    """Return Docker Compose status as JSON."""
    result = subprocess.run(
        ["docker", "compose", "ps", "-a", "--format", "json"],
        cwd=DB_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def verify_phase_0() -> bool:
    """Verify basic project structure."""
    required = [
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        ".env.example",
        "config/settings.yaml",
        "src/panganwatch/db.py",
    ]
    return all((DB_DIR / name).exists() for name in required)


def verify_phase_1() -> bool:
    """Verify Postgres, Mongo, Kafka, topics, and governance tables."""
    if not verify_phase_0():
        return False

    try:
        ps_output = _docker_ps_json()
    except Exception:
        return False

    status: dict[str, dict[str, str]] = {}
    for line in ps_output.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        service = item.get("Service")
        if service:
            status[service] = item

    required = {"postgres", "mongo", "kafka"}
    if not required.issubset(status):
        return False

    for service in required:
        if status[service].get("State") != "running" or "healthy" not in status[service].get(
            "Status", ""
        ):
            return False

    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'governance')")
            if not cur.fetchone()[0]:
                return False
            cur.execute("SELECT to_regclass('governance.pipeline_runs') IS NOT NULL")
            if not cur.fetchone()[0]:
                return False
        conn.close()
    except Exception:
        return False

    return True


def init_database() -> None:
    """Connect to Postgres and apply governance DDL."""
    conn = get_postgres_connection()
    try:
        apply_governance_ddl(conn)
    finally:
        conn.close()


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PanganWatch DB utilities")
    parser.add_argument("--init", action="store_true", help="Run governance DDL idempotently")
    args = parser.parse_args()

    if args.init:
        init_database()
        print("Governance DDL applied")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
