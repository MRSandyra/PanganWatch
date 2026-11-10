from src.silver import HDX_WFP_NATIONAL_MARKET, HDX_WFP_NATIONAL_PROVINCE_CODE


def test_hdx_wfp_national_mapping_is_explicit_and_does_not_invent_regional_codes():
    assert HDX_WFP_NATIONAL_MARKET == "national average"
    assert HDX_WFP_NATIONAL_PROVINCE_CODE == "00"
