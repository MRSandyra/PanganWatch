# Source inventory and licensing

| Source | Repository evidence | Intended snapshot | License / handling |
|---|---|---|---|
| HDX/WFP Indonesia Food Prices | `hdx_wfp.py:RESOURCE_URL`; README attribution | CSV, raw source rows | CC BY-IGO; retain attribution and URL |
| Open-Meteo Archive | `open_meteo.py:ARCHIVE_URL` | source-native JSON responses | CC BY 4.0; respect free non-commercial terms in README |
| BPS WebAPI | `bps.py:BASE_URL`, variables 2245/2249 | JSON only with permitted access | terms not verified; do not redistribute until checked |
| Province / commodity crosswalks | `dbt/panganwatch/seeds/` | committed reference seed extracts | source attribution remains in existing docs |

No raw snapshot was found under the ignored `data/raw/` path during the baseline audit. A new snapshot must be exported from a specifically selected permitted source file or historical Bronze extract, then run through both systems. An existing Silver-only extract may support a labeled Silver-to-Gold comparison, never raw-to-Silver parity.
