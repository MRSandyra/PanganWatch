"""Build dbt seed ref_ihk_kota.csv: BPS IHK city (vervar) -> kab/kota -> province (F3b/F5).

Input: the stored bronze payload of BPS var 2245 (no API call, no key needed) and
the existing seeds ref_kabkota.csv / ref_provinsi.csv. Match methods follow the
crosswalk convention (ref_crosswalk_wilayah): `normalized_name` (automatic) and
`manual` (BPS IHK names that are not administrative names, e.g. MEULABOH is the
IHK city of Kabupaten Aceh Barat). Anything that cannot be mapped is written with
an empty kode_provinsi_bps and REPORTED in docs/governance/ihk_mapping_report.md.

Run: uv run python scripts/build_ref_ihk_kota.py
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from panganwatch.db import get_mongo_client

SEEDS = Path("dbt/panganwatch/seeds")
OUT_CSV = SEEDS / "ref_ihk_kota.csv"
OUT_MD = Path("docs/governance/ihk_mapping_report.md")

# BPS IHK "city" names that are not administrative names -> official ref_kabkota name.
MANUAL_KABKOTA = {
    "MEULABOH": "Kabupaten Aceh Barat",
    "TEMBILAHAN": "Kabupaten Indragiri Hilir",
    "MUARA BUNGO": "Kabupaten Bungo",
    "TANJUNG PANDAN": "Kabupaten Belitung",
    "CILACAP": "Kabupaten Cilacap",
    "PURWOKERTO": "Kabupaten Banyumas",
    "KUDUS": "Kabupaten Kudus",
    "JEMBER": "Kabupaten Jember",
    "BANYUWANGI": "Kabupaten Banyuwangi",
    "SUMENEP": "Kabupaten Sumenep",
    "SINGARAJA": "Kabupaten Buleleng",
    "WAINGAPU": "Kabupaten Sumba Timur",
    "MAUMERE": "Kabupaten Sikka",
    "SINTANG": "Kabupaten Sintang",
    "SAMPIT": "Kabupaten Kotawaringin Timur",
    "KOTABARU": "Kabupaten Kotabaru",
    "TANJUNG": "Kabupaten Tabalong",
    "TANJUNG SELOR": "Kabupaten Bulungan",
    "LUWUK": "Kabupaten Banggai",
    "BULUKUMBA": "Kabupaten Bulukumba",
    "WATAMPONE": "Kabupaten Bone",
    "MAMUJU": "Kabupaten Mamuju",
    "MANOKWARI": "Kabupaten Manokwari",
    "MERAUKE": "Kabupaten Merauke",
    "TIMIKA": "Kabupaten Mimika",
    # Upstream ref_kabkota (cahyadsn/wilayah) names kode 16.02 "Kabupaten Ogan Komering"
    # (ibu kota Kayu Agung = ibu kota Kabupaten Ogan Komering Ilir); BPS says "... Ilir".
    "KAB OGAN KOMERING ILIR": "Kabupaten Ogan Komering",
}
# The Jakarta IHK city spans several administrative cities: map to the province only.
MANUAL_PROVINCE = {
    "KOTA JAKARTA": (
        "31",
        "IHK Jakarta mencakup beberapa kota administrasi; dipetakan ke provinsi DKI Jakarta saja",
    )
}


def squash(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"^kab\b\.?\s*", "kabupaten ", n)
    return re.sub(r"[^a-z0-9]", "", n)


def load_vervar() -> list[tuple[int, str]]:
    load_dotenv()
    client = get_mongo_client()
    try:
        coll = client.get_database(os.getenv("MONGO_DB", "bronze"))["bps_inflation"]
        doc = coll.find_one({"_meta.params.var": 2245}, sort=[("_meta.params.th", -1)])
        if doc is None:
            raise SystemExit(
                "no bronze bps_inflation payload for var 2245: run `python -m panganwatch.sources.bps --run` first"
            )
        return [(int(v["val"]), str(v["label"]).strip()) for v in doc["payload"]["vervar"]]
    finally:
        client.close()


def main() -> None:
    with (SEEDS / "ref_kabkota.csv").open(encoding="utf-8", newline="") as f:
        kabkota = list(csv.DictReader(f))
    by_squash = {squash(r["nama"]): r for r in kabkota}
    by_name = {r["nama"]: r for r in kabkota}

    rows, excluded = [], []
    for vervar, label in load_vervar():
        if label.upper() == "INDONESIA":
            excluded.append((vervar, label, "national aggregate, not a city"))
            continue
        target, method, reason = None, "", ""
        if label.upper() in MANUAL_KABKOTA:
            target = by_name.get(MANUAL_KABKOTA[label.upper()])
            method = "manual"
            reason = f"Nama kota IHK BPS bukan nama administrasi; dipetakan ke {MANUAL_KABKOTA[label.upper()]}"
            if target is None:
                reason = f"Target manual {MANUAL_KABKOTA[label.upper()]} tidak ada di ref_kabkota"
                method = ""
        elif label.upper() in MANUAL_PROVINCE:
            prov, reason = MANUAL_PROVINCE[label.upper()]
            rows.append((vervar, label, "", prov, "manual", reason))
            continue
        else:
            target = by_squash.get(squash(label))
            if target:
                method, reason = (
                    "normalized_name",
                    f"Nama BPS '{label}' cocok dengan '{target['nama']}' setelah normalisasi",
                )
            else:
                reason = "Tidak ada padanan nama di ref_kabkota"
        if target:
            rows.append(
                (vervar, label, target["kode_bps"], target["kode_provinsi_bps"], method, reason)
            )
        else:
            rows.append((vervar, label, "", "", "", reason))

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "kode_vervar",
                "nama_bps",
                "kode_kabkota_bps",
                "kode_provinsi_bps",
                "match_method",
                "alasan",
            ]
        )
        w.writerows(rows)

    unmapped = [r for r in rows if not r[3]]
    methods = Counter(r[4] or "unmapped" for r in rows)
    provs = {r[3] for r in rows if r[3]}
    lines = [
        "# BPS IHK city -> province mapping (`ref_ihk_kota`)",
        "",
        "Generated by `scripts/build_ref_ihk_kota.py` from the BPS var-2245 bronze payload and the `ref_kabkota` seed (not ad hoc query-time matching).",
        "",
        f"- IHK cities: **{len(rows)}** (+ {len(excluded)} aggregate(s) excluded: {', '.join(e[1] for e in excluded)})",
        f"- Mapped to a province: **{len(rows) - len(unmapped)}** of {len(rows)}; distinct provinces: **{len(provs)}**",
        "- By method: " + ", ".join(f"{k}={v}" for k, v in sorted(methods.items())),
        f"- **Unmapped: {len(unmapped)}**",
        "",
    ]
    if unmapped:
        lines += ["| kode_vervar | BPS name | reason |", "|---|---|---|"]
        lines += [f"| {r[0]} | {r[1]} | {r[5]} |" for r in unmapped]
    else:
        lines += ["All IHK cities are mapped."]
    manual = [r for r in rows if r[4] == "manual"]
    lines += [
        "",
        f"## Manual mappings ({len(manual)}) — need human review",
        "",
        "BPS IHK city names that are not administrative names (e.g. MEULABOH = the IHK city for Kabupaten Aceh Barat), plus one naming mismatch with the seed source.",
        "",
        "| kode_vervar | BPS name | kab/kota code | province code | reason |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r[0]} | {r[1]} | {r[2] or '-'} | {r[3]} | {r[5]} |" for r in manual]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT_CSV} ({len(rows)} rows) and {OUT_MD}; methods={dict(methods)}; unmapped={len(unmapped)}; provinces={len(provs)}"
    )
    for r in unmapped:
        print("UNMAPPED:", r[0], r[1], "-", r[5])


if __name__ == "__main__":
    main()
