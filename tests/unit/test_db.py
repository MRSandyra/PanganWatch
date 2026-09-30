from __future__ import annotations

from types import SimpleNamespace

import panganwatch.db as db


def test_get_env_var_reads_default(monkeypatch):
    monkeypatch.delenv("MISSING_ENV", raising=False)
    assert db.get_env_var("MISSING_ENV", "fallback") == "fallback"


def test_get_postgres_connection_uses_env(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(db, "psycopg", SimpleNamespace(connect=fake_connect))
    monkeypatch.setenv("POSTGRES_HOST", "pg")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("POSTGRES_DB", "panganwatch")
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    db.get_postgres_connection()

    assert calls["host"] == "pg"
    assert calls["port"] == 15432
    assert calls["dbname"] == "panganwatch"
    assert calls["user"] == "user"
    assert calls["password"] == "secret"


def test_get_mongo_client_uses_env(monkeypatch):
    calls = {}

    class FakeMongoClient:
        def __init__(self, uri, **kwargs):
            calls["uri"] = uri
            calls.update(kwargs)

    monkeypatch.setattr(db, "MongoClient", FakeMongoClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://mongo:27017")

    db.get_mongo_client()

    assert calls["uri"] == "mongodb://mongo:27017"
    assert calls["serverSelectionTimeoutMS"] == 5000


def test_apply_governance_ddl_executes_sql(monkeypatch):
    executed = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql):
            executed.append(sql)

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            executed.append("COMMIT")

    monkeypatch.setattr(db, "read_governance_ddl", lambda: "select 1;")
    db.apply_governance_ddl(FakeConn())

    assert executed == ["select 1;", "COMMIT"]
