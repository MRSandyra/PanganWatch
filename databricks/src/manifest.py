"""Immutable snapshot manifests and checksum validation, independent of Spark."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "snapshot_id",
    "source_name",
    "source_url",
    "license",
    "schema_version",
    "source_period_start",
    "source_period_end",
    "fetched_at_utc",
    "file_name",
    "file_format",
    "record_count",
    "sha256",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_records(path: Path, file_format: str) -> int:
    if file_format == "csv":
        return max(0, len(path.read_text(encoding="utf-8-sig").splitlines()) - 1)
    if file_format == "jsonl":
        return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())
    if file_format == "json":
        value = json.loads(path.read_text(encoding="utf-8"))
        return len(value) if isinstance(value, list) else 1
    raise ValueError(f"Unsupported snapshot format: {file_format}")


def build_manifest(
    path: Path,
    *,
    source_name: str,
    source_url: str,
    license_name: str,
    schema_version: str = "1.0",
    source_period_start: str | None = None,
    source_period_end: str | None = None,
    fetched_at_utc: str | None = None,
) -> dict[str, Any]:
    file_format = path.suffix.lower().lstrip(".")
    if file_format == "ndjson":
        file_format = "jsonl"
    checksum = sha256_file(path)
    stable = f"{source_name}|{path.name}|{checksum}".encode()
    return {
        "snapshot_id": hashlib.sha256(stable).hexdigest()[:24],
        "source_name": source_name,
        "source_url": source_url,
        "license": license_name,
        "schema_version": schema_version,
        "source_period_start": source_period_start,
        "source_period_end": source_period_end,
        "fetched_at_utc": fetched_at_utc or datetime.now(UTC).isoformat(),
        "file_name": path.name,
        "file_format": file_format,
        "record_count": count_records(path, file_format),
        "sha256": checksum,
    }


def validate_manifest(manifest: dict[str, Any], data_path: Path | None = None) -> None:
    missing = REQUIRED_FIELDS - manifest.keys()
    if missing:
        raise ValueError(f"Manifest missing fields: {sorted(missing)}")
    if not isinstance(manifest["record_count"], int) or manifest["record_count"] < 0:
        raise ValueError("Manifest record_count must be a non-negative integer")
    if len(manifest["sha256"]) != 64 or any(
        c not in "0123456789abcdef" for c in manifest["sha256"]
    ):
        raise ValueError("Manifest sha256 is invalid")
    if data_path:
        if sha256_file(data_path) != manifest["sha256"]:
            raise ValueError("Snapshot checksum mismatch")
        if count_records(data_path, manifest["file_format"]) != manifest["record_count"]:
            raise ValueError("Snapshot record count mismatch")


def write_manifest(manifest: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
