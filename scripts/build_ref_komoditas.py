"""Generate ref_komoditas and ref_komoditas_alias seeds with improved matching logic.

Read config/settings.yaml for the target commodities (komoditas_list).

Each commodity has:
- komoditas_id: a 4-digit zero-padded code (e.g. 0101)
- nama_kanonis: the canonical name (a single word, no qualifiers; e.g. "beras" not "beras makanan")
- kelompok: beras, cabai, bawang, daging, gula, minyak, telur (the standard F2 groups)
- satuan: kg, liter, butir, pcs, pak (adjust as needed)
- het: an empty (nullable) column; filled in if an official source has an HET

Aliases: take names from data sources (e.g. an API) and normalize them to the matching komoditas_id.
"""

import csv
import re
from pathlib import Path

OUT_CSV_DIR = Path("dbt/panganwatch/seeds")
OUT_CSV_KOMODITAS = OUT_CSV_DIR / "ref_komoditas.csv"
OUT_CSV_ALIAS = OUT_CSV_DIR / "ref_komoditas_alias.csv"

# Deterministic mapping for F2 (based on the config/settings.yaml commodities)
KOMODITAS_LIST = [
    {
        "komoditas_id": "0101",
        "nama_kanonis": "beras",
        "kelompok": "beras",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0102",
        "nama_kanonis": "cabai rawit",
        "kelompok": "cabai",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0103",
        "nama_kanonis": "cabai besar",
        "kelompok": "cabai",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0104",
        "nama_kanonis": "bawang merah",
        "kelompok": "bawang",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0105",
        "nama_kanonis": "bawang putih",
        "kelompok": "bawang",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0106",
        "nama_kanonis": "daging sapi",
        "kelompok": "daging",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0107",
        "nama_kanonis": "telur ayam",
        "kelompok": "telur",
        "satuan": "butir",
        "het": None,
    },
    {
        "komoditas_id": "0108",
        "nama_kanonis": "minyak goreng",
        "kelompok": "minyak",
        "satuan": "liter",
        "het": None,
    },
    {
        "komoditas_id": "0109",
        "nama_kanonis": "gula pasir",
        "kelompok": "gula",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0110",
        "nama_kanonis": "telur bebek",
        "kelompok": "telur",
        "satuan": "butir",
        "het": None,
    },
    {
        "komoditas_id": "0111",
        "nama_kanonis": "daging ayam",
        "kelompok": "daging",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0112",
        "nama_kanonis": "minyak kelapa",
        "kelompok": "minyak",
        "satuan": "liter",
        "het": None,
    },
    {
        "komoditas_id": "0113",
        "nama_kanonis": "gula merah",
        "kelompok": "gula",
        "satuan": "kg",
        "het": None,
    },
    {
        "komoditas_id": "0114",
        "nama_kanonis": "cabai keriting",
        "kelompok": "cabai",
        "satuan": "kg",
        "het": None,
    },
]


# Normalize a source name: strip numbers, units, punctuation, reduce to the base word
def normalize_source_name(name: str) -> str:
    s = name.lower().strip()
    # Strip numbers and common units
    s = re.sub(r"\b\d+\s*(kg|liter|butir|pcs|pak|stadium|cent)\s*", " ", s)
    s = re.sub(r"\([^)]*\)", " ", s)  # Strip parentheses and their contents
    s = re.sub(r"\[[^\]]*\]", " ", s)
    # Strip special characters
    s = re.sub(r"[^\w\s]", " ", s)
    # Common qualifier words that can be dropped
    stopwords = [
        "medium",
        "stadium",
        "pangan",
        "segar",
        "kualitas",
        "grade",
        "premium",
        "ras",
        "kampung",
        "jenis",
        "murah",
        "mahal",
        "box",
        "karung",
        "m3",
        "m2",
        "bungkus",
        "plastik",
        "ayam",
        "sapi",
        "burger",
        "rebus",
        "goreng",
        "iris",
    ]
    for sw in stopwords:
        s = re.sub(r"\b" + sw + r"\b", "", s)
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Names from the various sources (tuned for better matching)
SOURCE_NAMES = {
    "PIHPS": [
        "Beras Medium Stadion (30 kg)",
        "Cabai Merah Keriting 1 kg",
        "Bawang Merah 1 kg",
        "Daging Sapi Segar 1 kg",
        "Telur Ayam Kampung 1 kg",
        "Minyak Goreng Sawit 1 liter",
        "Gula Pasir Putih 1 kg",
        "Telur Bebek 1 kg",
        "Daging Ayam Boiler 1 kg",
        "Minyak Kelapa 1 liter",
        "Gula Merah 1 kg",
        "Cabai Rawit 1 kg",
        "Bawang Putih 1 kg",
        "Telur Ayam Ras 1 kg",
    ],
    "BPS": [
        "Beras Medium (30 kg)",
        "Cabai Merah Keriting (1 kg)",
        "Bawang Merah (1 kg)",
        "Daging Sapi Segar (1 kg)",
        "Telur Ayam Kampung (1 kg)",
        "Minyak Goreng (1 liter)",
        "Gula Pasir (1 kg)",
        "Telur Bebek (1 kg)",
        "Daging Ayam (1 kg)",
        "Minyak Kelapa (1 liter)",
        "Gula Merah (1 kg)",
        "Cabai Rawit (1 kg)",
        "Bawang Putih (1 kg)",
        "Telur Ayam Ras (1 kg)",
    ],
    "Kemendagri": [
        "Beras Medium",
        "Cabai Merah",
        "Bawang Merah",
        "Daging Sapi",
        "Telur Ayam",
        "Minyak Goreng",
        "Gula Pasir",
        "Telur Bebek",
        "Daging Ayam",
        "Minyak Kelapa",
        "Gula Merah",
        "Cabai Rawit",
        "Bawang Putih",
        "Telur Ayam Ras",
    ],
}

# Names from Indonesian sources that don't match via normalization/contains
# (e.g. different word order: "Cabai Merah Keriting" vs. canonical "cabai keriting").
# Mapped manually with a reason, rather than left as an 'XXXX' placeholder.
MANUAL_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    ("BPS", "Cabai Merah Keriting (1 kg)"): (
        "0114",
        "'Cabai Merah Keriting' = cabai keriting (0114); urutan kata beda dari nama kanonis sehingga tidak match otomatis",
    ),
    ("PIHPS", "Cabai Merah Keriting 1 kg"): (
        "0114",
        "'Cabai Merah Keriting' = cabai keriting (0114); urutan kata beda dari nama kanonis sehingga tidak match otomatis",
    ),
    ("Kemendagri", "Cabai Merah"): (
        "0103",
        "'Cabai Merah' generik (tanpa kualifier rawit/keriting) mengacu ke cabai besar (0103) dalam konvensi pemantauan harga Kemendagri",
    ),
}

# WFP/HDX reports commodity names in English, so string normalization against
# the (Indonesian) canonical name doesn't apply; the semantic mapping is done
# manually here, once, and the result is stored as a seed.
# Names are taken from data/raw/wfp_food_prices_idn.csv.
# Fuel (kerosene), Milk (condensed), and Wheat flour are deliberately NOT mapped:
# there is no matching commodity group in ref_komoditas (the 14 F2 rows), so rows
# with these commodities will be quarantined during ingestion (F3a).
HDX_MANUAL_MAP: dict[str, tuple[str, str]] = {
    "Rice": ("0101", "beras (generik)"),
    "Rice (high quality)": ("0101", "beras kualitas tinggi -> kelompok beras"),
    "Rice (low quality)": ("0101", "beras kualitas rendah -> kelompok beras"),
    "Rice (medium quality)": ("0101", "beras kualitas medium -> kelompok beras"),
    "Chili (bird's eye)": ("0102", "cabai rawit (bird's eye chili)"),
    "Chili (bird's eye, green)": ("0102", "cabai rawit hijau -> cabai rawit"),
    "Chili (bird's eye, red)": ("0102", "cabai rawit merah -> cabai rawit"),
    "Chili (red)": ("0103", "cabai merah besar generik -> cabai besar"),
    "Chili (red, large)": ("0103", "cabai merah besar -> cabai besar"),
    "Chili (red, curly)": ("0114", "cabai merah keriting -> cabai keriting"),
    "Onions (shallot)": ("0104", "bawang merah (shallot)"),
    "Onions (shallot, medium)": ("0104", "bawang merah ukuran medium -> bawang merah"),
    "Garlic": ("0105", "bawang putih (garlic)"),
    "Garlic (medium)": ("0105", "bawang putih ukuran medium -> bawang putih"),
    "Meat (beef)": ("0106", "daging sapi (beef)"),
    "Meat (beef, first quality)": ("0106", "daging sapi kualitas 1 -> daging sapi"),
    "Meat (beef, second quality)": ("0106", "daging sapi kualitas 2 -> daging sapi"),
    "Meat (chicken)": ("0111", "daging ayam (chicken)"),
    "Meat (chicken, broiler)": ("0111", "daging ayam broiler -> daging ayam"),
    "Eggs": (
        "0107",
        "telur generik; dataset WFP Indonesia mayoritas melaporkan telur ayam ras -> telur ayam",
    ),
    "Eggs (broiler)": ("0107", "telur ayam broiler -> telur ayam"),
    "Oil (vegetable)": ("0108", "minyak goreng nabati (vegetable oil) -> minyak goreng"),
    "Oil (vegetable, bulk)": ("0108", "minyak goreng curah -> minyak goreng"),
    "Oil (vegetable, packaged)": ("0108", "minyak goreng kemasan -> minyak goreng"),
    "Sugar": ("0109", "gula pasir generik"),
    "Sugar (local)": ("0109", "gula pasir lokal -> gula pasir"),
    "Sugar (premium)": ("0109", "gula pasir premium -> gula pasir"),
}

# Build the alias list with improved matching
crosswalk = []
for source, names in SOURCE_NAMES.items():
    for src_name in names:
        norm_src = normalize_source_name(src_name)
        matched = False
        for k in KOMODITAS_LIST:
            norm_kanonis = normalize_source_name(k["nama_kanonis"])
            if norm_src == norm_kanonis:
                crosswalk.append(
                    {
                        "komoditas_id": k["komoditas_id"],
                        "nama_sumber": src_name,
                        "sumber": source,
                        "match_method": "normalized_name",
                        "alasan": f"'{src_name}' cocok dengan nama kanonis '{k['nama_kanonis']}' (normalized)",
                    }
                )
                matched = True
                break
            # Also try simple contains check for better matching
            if norm_src in norm_kanonis or norm_kanonis in norm_src:
                crosswalk.append(
                    {
                        "komoditas_id": k["komoditas_id"],
                        "nama_sumber": src_name,
                        "sumber": source,
                        "match_method": "normalized_name",
                        "alasan": f"'{src_name}' cocok dengan nama kanonis '{k['nama_kanonis']}' (contains)",
                    }
                )
                matched = True
                break
        if not matched and (source, src_name) in MANUAL_OVERRIDES:
            komoditas_id, alasan = MANUAL_OVERRIDES[(source, src_name)]
            crosswalk.append(
                {
                    "komoditas_id": komoditas_id,
                    "nama_sumber": src_name,
                    "sumber": source,
                    "match_method": "manual",
                    "alasan": alasan,
                }
            )
            matched = True
        if not matched:
            raise SystemExit(
                f"No match (auto or manual) for source={source!r} name={src_name!r}; "
                "add an entry to MANUAL_OVERRIDES instead of leaving a placeholder id."
            )

for hdx_name, (komoditas_id, alasan) in HDX_MANUAL_MAP.items():
    crosswalk.append(
        {
            "komoditas_id": komoditas_id,
            "nama_sumber": hdx_name,
            "sumber": "HDX",
            "match_method": "manual",
            "alasan": f"'{hdx_name}' -> {alasan}",
        }
    )

# Write CSV
OUT_CSV_DIR.mkdir(parents=True, exist_ok=True)
# Commodities
with OUT_CSV_KOMODITAS.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["komoditas_id", "nama_kanonis", "kelompok", "satuan", "het"]
    )
    writer.writeheader()
    for k in KOMODITAS_LIST:
        writer.writerow(
            {
                "komoditas_id": k["komoditas_id"],
                "nama_kanonis": k["nama_kanonis"],
                "kelompok": k["kelompok"],
                "satuan": k["satuan"],
                "het": k["het"],
            }
        )

# Aliases
with OUT_CSV_ALIAS.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["komoditas_id", "nama_sumber", "sumber", "match_method", "alasan"]
    )
    writer.writeheader()
    writer.writerows(crosswalk)

print(f"Wrote {len(KOMODITAS_LIST)} commodities to {OUT_CSV_KOMODITAS}")
print(f"Wrote {len(crosswalk)} aliases to {OUT_CSV_ALIAS}")
print(
    f"Total normalized_name: {len([a for a in crosswalk if a['match_method'] == 'normalized_name'])}"
)
print(f"Total manual: {len([a for a in crosswalk if a['match_method'] == 'manual'])}")
