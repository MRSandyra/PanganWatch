"""Bronze layer helpers (AD-01, AD-02, AD-03, AD-04).

Every raw payload ingested from an external source is wrapped in a `_meta`
envelope and stored in MongoDB. `store_raw` is idempotent: the unique index on
`(_meta.source, _meta.payload_sha256)` means re-running an ingestion for the
same payload does not create a duplicate bronze document.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from panganwatch.db import get_mongo_client

SCHEMA_VERSION = "1.0"
TTL_SECONDS = 90 * 24 * 60 * 60  # AD-04: 90 days


def _mongo_db_name(mongo_db: str | None) -> str:
    return mongo_db or os.getenv("MONGO_DB", "bronze")


def _payload_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def ensure_bronze_indexes(collection: str, mongo_db: str | None = None) -> None:
    """Create the AD-03 unique index and AD-04 TTL index if they don't exist yet."""
    client = get_mongo_client()
    try:
        db = client.get_database(_mongo_db_name(mongo_db))
        coll = db[collection]
        coll.create_index(
            [("_meta.source", 1), ("_meta.payload_sha256", 1)],
            unique=True,
            name="ux_meta_source_payload_sha256",
        )
        coll.create_index(
            "_meta.fetched_at",
            expireAfterSeconds=TTL_SECONDS,
            name="ttl_90_days_fetched_at",
        )
    finally:
        client.close()


def store_raw(
    source: str,
    endpoint: str,
    params: dict[str, Any],
    payload: Any,
    http_status: int,
    run_id: str,
    collection: str,
    mongo_db: str | None = None,
) -> str | None:
    """Store a raw payload in MongoDB bronze with the AD-02 envelope.

    Returns the inserted document's id as a string, or None if this exact
    payload (same source + sha256) was already stored (idempotent no-op).
    """
    ensure_bronze_indexes(collection, mongo_db=mongo_db)

    envelope = {
        "source": source,
        "endpoint": endpoint,
        "params": params,
        "fetched_at": datetime.now(UTC),
        "run_id": run_id,
        "http_status": http_status,
        "payload_sha256": _payload_sha256(payload),
        "schema_version": SCHEMA_VERSION,
    }
    document = {"_meta": envelope, "payload": payload}

    client = get_mongo_client()
    try:
        db = client.get_database(_mongo_db_name(mongo_db))
        coll = db[collection]
        try:
            result = coll.insert_one(document)
            return str(result.inserted_id)
        except Exception as exc:  # duplicate key -> idempotent no-op
            if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
                return None
            raise
    finally:
        client.close()
