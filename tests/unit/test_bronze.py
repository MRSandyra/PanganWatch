from __future__ import annotations

import panganwatch.bronze as bronze


class FakeCollection:
    def __init__(self, raise_duplicate: bool = False):
        self.indexes = []
        self.inserted = []
        self._raise_duplicate = raise_duplicate

    def create_index(self, keys, **kwargs):
        self.indexes.append((keys, kwargs))

    def insert_one(self, document):
        if self._raise_duplicate:
            raise Exception("E11000 duplicate key error collection")
        self.inserted.append(document)

        class Result:
            inserted_id = "abc123"

        return Result()


class FakeDB(dict):
    def __getitem__(self, name):
        return self.setdefault(name, FakeCollection())


class FakeClient:
    def __init__(self, db: FakeDB):
        self._db = db

    def get_database(self, name=None):
        return self._db

    def close(self):
        pass


def test_store_raw_builds_ad02_envelope(monkeypatch):
    coll = FakeCollection()
    db = FakeDB()
    db["hdx_wfp_prices"] = coll
    monkeypatch.setattr(bronze, "get_mongo_client", lambda: FakeClient(db))

    inserted_id = bronze.store_raw(
        source="hdx_wfp",
        endpoint="https://example.com/data.csv",
        params={"month": "2026-06"},
        payload=[{"a": 1}],
        http_status=200,
        run_id="run-1",
        collection="hdx_wfp_prices",
    )

    assert inserted_id == "abc123"
    assert len(coll.inserted) == 1
    envelope = coll.inserted[0]["_meta"]
    for field in (
        "source",
        "endpoint",
        "params",
        "fetched_at",
        "run_id",
        "http_status",
        "payload_sha256",
        "schema_version",
    ):
        assert field in envelope
    assert envelope["source"] == "hdx_wfp"
    assert envelope["schema_version"] == bronze.SCHEMA_VERSION


def test_ensure_bronze_indexes_creates_unique_and_ttl(monkeypatch):
    coll = FakeCollection()
    db = FakeDB()
    db["hdx_wfp_prices"] = coll
    monkeypatch.setattr(bronze, "get_mongo_client", lambda: FakeClient(db))

    bronze.ensure_bronze_indexes("hdx_wfp_prices")

    names = [kwargs.get("name") for _, kwargs in coll.indexes]
    assert "ux_meta_source_payload_sha256" in names
    assert "ttl_90_days_fetched_at" in names
    ttl_kwargs = next(
        kwargs for _, kwargs in coll.indexes if kwargs.get("name") == "ttl_90_days_fetched_at"
    )
    assert ttl_kwargs["expireAfterSeconds"] == 90 * 24 * 60 * 60


def test_store_raw_is_idempotent_on_duplicate_payload(monkeypatch):
    coll = FakeCollection(raise_duplicate=True)
    db = FakeDB()
    db["hdx_wfp_prices"] = coll
    monkeypatch.setattr(bronze, "get_mongo_client", lambda: FakeClient(db))

    result = bronze.store_raw(
        source="hdx_wfp",
        endpoint="https://example.com/data.csv",
        params={},
        payload=[{"a": 1}],
        http_status=200,
        run_id="run-1",
        collection="hdx_wfp_prices",
    )

    assert result is None  # duplicate -> no-op, not an error
