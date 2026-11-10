from pathlib import Path

from src.silver import HDX_WFP_NATIONAL_MARKET, HDX_WFP_NATIONAL_PROVINCE_CODE


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
