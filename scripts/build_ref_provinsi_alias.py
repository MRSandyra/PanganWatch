"""F3a: build ref_provinsi_alias seed.

Maps province names as they appear in each price source's raw data to the
canonical `kode_bps` in `ref.ref_provinsi`, via generic normalization
(lowercase, strip punctuation, collapse whitespace) plus a small, documented
manual-override table for names that don't normalize-match anything (e.g.
common abbreviations like "DKI Jakarta").

This replaces ad-hoc per-name dictionaries inside ingestion code with a
reviewable seed, consistent with AD-14.

Sources:
- Province admin1 values: HDX "Indonesia - Food Prices" dataset, resource
  wfp_food_prices_idn.csv (https://data.humdata.org/dataset/wfp-food-prices-for-indonesia),
  cached at data/raw/wfp_food_prices_idn.csv.
- Canonical province names: dbt/panganwatch/seeds/ref_provinsi.csv (F2).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_PROVINSI_SEED = ROOT / "dbt" / "panganwatch" / "seeds" / "ref_provinsi.csv"
WFP_CSV = ROOT / "data" / "raw" / "wfp_food_prices_idn.csv"
OUT_SEED = ROOT / "dbt" / "panganwatch" / "seeds" / "ref_provinsi_alias.csv"

# Names that don't normalize-match any ref_provinsi.nama_provinsi, mapped by
# hand with a documented reason. Keep this list as short as possible; prefer
# fixing the normalization function over adding entries here.
MANUAL_OVERRIDES: dict[str, tuple[str, str]] = {
    "DKI JAKARTA": (
        "31",
        "'DKI Jakarta' adalah singkatan umum resmi untuk provinsi "
        "'Daerah Khusus Ibukota Jakarta' (kode BPS 31); tidak cocok dengan "
        "normalisasi string biasa karena kata-katanya berbeda.",
    ),
}


def normalize(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_ref_provinsi() -> list[dict[str, str]]:
    with REF_PROVINSI_SEED.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_wfp_admin1() -> list[str]:
    values: set[str] = set()
    with WFP_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            admin1 = (row.get("admin1") or "").strip()
            if admin1:
                values.add(admin1)
    return sorted(values)


def main() -> int:
    provinces = load_ref_provinsi()
    norm_to_kode = {normalize(p["nama_provinsi"]): p["kode_bps"] for p in provinces}

    admin1_values = load_wfp_admin1()
    rows = []
    unmatched = []
    for raw_name in admin1_values:
        norm = normalize(raw_name)
        if norm in norm_to_kode:
            rows.append(
                {
                    "nama_sumber": raw_name,
                    "sumber": "HDX",
                    "kode_bps": norm_to_kode[norm],
                    "match_method": "normalized_name",
                    "alasan": f"'{raw_name}' cocok dengan nama_provinsi setelah normalisasi",
                }
            )
        elif raw_name in MANUAL_OVERRIDES:
            kode_bps, alasan = MANUAL_OVERRIDES[raw_name]
            rows.append(
                {
                    "nama_sumber": raw_name,
                    "sumber": "HDX",
                    "kode_bps": kode_bps,
                    "match_method": "manual",
                    "alasan": alasan,
                }
            )
        else:
            unmatched.append(raw_name)

    OUT_SEED.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SEED.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["nama_sumber", "sumber", "kode_bps", "match_method", "alasan"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} province aliases to {OUT_SEED}")
    print(f"  normalized_name: {sum(1 for r in rows if r['match_method'] == 'normalized_name')}")
    print(f"  manual: {sum(1 for r in rows if r['match_method'] == 'manual')}")
    if unmatched:
        print(f"UNMATCHED ({len(unmatched)}): {unmatched}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
