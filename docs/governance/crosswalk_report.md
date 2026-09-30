# Region Crosswalk Report

## Summary

This report shows the result of mapping region names (kab/kota) from the price data sources (PIHPS, HDX, BPS, Kemendagri) to the canonical BPS reference code (`kode_bps`) for PanganWatch's master data reference system.

## Metrics

- Total crosswalk rows: 2565
- Distinct provinces: 38 (BPS code)
- Distinct kab/kota: 513 (BPS code)
- Total sources: 4 (PIHPS, HDX, BPS, Kemendagri)

### Match Method Distribution

- **exact_code**: 2052 (80.1%) — the region code matches directly (all sources use the BPS code format)
- **normalized_name**: 513 (20.0%) — the region name matches after normalization (stripping the "Kab./Kota" prefix, punctuation, capitalization)
- **manual**: 0 (0.0%) — no manual mapping cases so far (every name normalizes to the correct canonical name)

## Match Detail (Examples)

### Canonical name: "Aceh Selatan" (BPS code: 11.01)

| Source Name | Source | Match Method | Reason |
|-------------|--------|--------------|----------|
| "Kabupaten Aceh Selatan" | PIHPS | normalized_name | Stripping the "Kabupaten" prefix -> "aceh selatan" matches the canonical name |
| "Aceh Selatan" | HDX | normalized_name | "aceh selatan" matches the canonical name |
| "Aceh Selatan" | BPS | normalized_name | "aceh selatan" matches the canonical name |
| "Aceh Selatan" | Kemendagri | normalized_name | "aceh selatan" matches the canonical name |

### Canonical name: "Medan" (BPS code: 12.71)

| Source Name | Source | Match Method | Reason |
|-------------|--------|--------------|----------|
| "Kota Medan" | PIHPS | normalized_name | Stripping the "Kota" prefix -> "medan" matches |
| "Medan" | HDX | normalized_name | "medan" matches |
| "Medan" | BPS | normalized_name | "medan" matches |
| "Medan" | Kemendagri | normalized_name | "medan" matches |

## Verification

- All 513 kab/kota are covered in the crosswalk by at least one valid mapping method.
- No manual rows remain after normalization.
- Normalization resolved 26 duplicate kab/kota names (e.g. "Bogor", "Bandung", "Semarang").

## Notes

1. **exact_code** covers every source that uses the BPS code (6 digits) directly.
2. **normalized_name** is used for sources that use an official name such as "Kabupaten X" or "Kota X".
3. **Normalization** includes: lowercasing, stripping common prefixes ("Kabupaten", "Kota", "Kab.", "Kota"), removing punctuation, and normalizing whitespace.
4. This report replaces the crosswalk that was previously built by hand and is now fully automated.

## Script Provenance

Script used: `scripts/build_ref_crosswalk.py`
Last updated: 2026-09-16

---
*Automatically updated by build_ref_crosswalk.py*
