from pathlib import Path

from src.silver import (
    HDX_WFP_GOVERNANCE_COLUMNS,
    HDX_WFP_NATIONAL_MARKET,
    HDX_WFP_NATIONAL_PROVINCE_CODE,
)


def test_hdx_wfp_national_mapping_is_explicit_and_does_not_invent_regional_codes():
    assert HDX_WFP_NATIONAL_MARKET == "national average"
    assert HDX_WFP_NATIONAL_PROVINCE_CODE == "00"


def test_silver_deduplicates_before_selecting_away_bronze_provenance():
    source = (Path(__file__).resolve().parents[1] / "src" / "silver.py").read_text(
        encoding="utf-8"
    )
    assert "deduplicate(typed, KEYS[dataset]).select" in source
    assert 'sf.col("_ingested_at")' in source
    assert 'sf.col("_source_sha256")' in source


def test_hdx_wfp_uses_committed_aliases_and_requires_an_explicit_rebuild():
    source = (Path(__file__).resolve().parents[1] / "src" / "silver.py").read_text(
        encoding="utf-8"
    )
    assert 'ref_provinsi_alias' in source
    assert 'ref_komoditas_alias' in source
    assert 'rebuild_hdx_wfp=true' in source


def test_hdx_wfp_normal_reruns_allow_already_resolved_silver_rows():
    source = (Path(__file__).resolve().parents[1] / "src" / "silver.py").read_text(
        encoding="utf-8"
    )
    assert 'reference_ids = spark.table(config.qualified("reference", "ref_komoditas"))' in source
    assert "if provisional_rows:" in source


def test_unmapped_governance_schema_excludes_temporary_reference_join_columns():
    assert "_admin1" not in HDX_WFP_GOVERNANCE_COLUMNS
    assert "_kode_provinsi_bps" not in HDX_WFP_GOVERNANCE_COLUMNS
    assert "_commodity" not in HDX_WFP_GOVERNANCE_COLUMNS
    assert "_komoditas_id" not in HDX_WFP_GOVERNANCE_COLUMNS
