import json
from pathlib import Path

import pytest

from src.manifest import build_manifest, validate_manifest, write_manifest


def test_manifest_is_deterministic_for_content(tmp_path: Path):
    source = tmp_path / "prices.csv"
    source.write_text("date,price\n2026-01-15,12000\n", encoding="utf-8")
    first = build_manifest(
        source,
        source_name="hdx_wfp",
        source_url="https://example.test",
        license_name="CC-BY-IGO",
        fetched_at_utc="2026-01-01T00:00:00+00:00",
    )
    second = build_manifest(
        source,
        source_name="hdx_wfp",
        source_url="https://example.test",
        license_name="CC-BY-IGO",
        fetched_at_utc="2026-02-01T00:00:00+00:00",
    )
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["record_count"] == 1
    destination = write_manifest(first, tmp_path / "manifest.json")
    assert json.loads(destination.read_text())["sha256"] == first["sha256"]
    validate_manifest(first, source)


def test_manifest_detects_tampered_snapshot(tmp_path: Path):
    source = tmp_path / "prices.csv"
    source.write_text("date,price\n2026-01-15,12000\n", encoding="utf-8")
    manifest = build_manifest(
        source, source_name="hdx_wfp", source_url="https://example.test", license_name="CC-BY-IGO"
    )
    source.write_text("date,price\n2026-01-15,99999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, source)
