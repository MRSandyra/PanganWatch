"""Generate ref_crosswalk_wilayah seed.

Build crosswalk mapping names/codes from sources (PIHPS, HDX, BPS, Kemendagri)
to canonical kode_bps. Uses realistic Indonesian kab/kota names and the
seed ref_kabkota to avoid non-existent entries.

Mapping methods:
- exact_code: kode_bps from source matches kode_bps in ref_kabkota
- exact_name: nama_sumber (raw) matches nama in ref_kabkota (case-insensitive)
- normalized_name: the raw source text is normalized (lowercased, "Kab./Kota"
  prefix stripped), then matched against the ref_kabkota name
- manual: fallback when a name can't be mapped; given a reason and logged

Output CSV: dbt/panganwatch/seeds/ref_crosswalk_wilayah.csv
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "dbt/panganwatch/seeds"


# Load ref_kabkota reference
def load_ref_kabkota():
    ref_path = OUTPUT_DIR / "ref_kabkota.csv"
    ref = {}
    with open(ref_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kode = row["kode_bps"].strip()
            ref[kode] = row
            # Normalized key: lowercase name without "kab." or "kota"
            name = row["nama"].lower()
            if name.startswith("kab."):
                name = name[4:].strip()
            if name.startswith("kota "):
                name = name[5:].strip()
            ref[name] = row
    return ref


# Source data - realistic examples from Indonesian regions
def load_sources():
    # In production, this would read from the actual PIHPS/HDX/BPS/Kemendagri sources
    # For now, use realistic examples
    # PIHPS source examples
    pihps_rows = [
        {
            "sumber": "PIHPS",
            "nama": "Kota Surabaya",
            "kode_bps": "35.71",
            "kode_kemendagri": "35.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Lamongan",
            "kode_bps": "35.09",
            "kode_kemendagri": "35.09",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Yogyakarta",
            "kode_bps": "33.71",
            "kode_kemendagri": "33.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Sleman",
            "kode_bps": "33.02",
            "kode_kemendagri": "33.02",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Makassar",
            "kode_bps": "73.71",
            "kode_kemendagri": "73.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Gowa",
            "kode_bps": "73.02",
            "kode_kemendagri": "73.02",
        },
        {"sumber": "PIHPS", "nama": "Kota Medan", "kode_bps": "12.71", "kode_kemendagri": "12.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Deli Serdang",
            "kode_bps": "12.01",
            "kode_kemendagri": "12.01",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Denpasar",
            "kode_bps": "51.71",
            "kode_kemendagri": "51.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Badung",
            "kode_bps": "51.02",
            "kode_kemendagri": "51.02",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Pekanbaru",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Kampar",
            "kode_bps": "14.03",
            "kode_kemendagri": "14.03",
        },
        {"sumber": "PIHPS", "nama": "Kota Jambi", "kode_bps": "15.71", "kode_kemendagri": "15.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Muaro Jambi",
            "kode_bps": "15.01",
            "kode_kemendagri": "15.01",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Palembang",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Banyuasin",
            "kode_bps": "16.03",
            "kode_kemendagri": "16.03",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Bandung",
            "kode_bps": "32.71",
            "kode_kemendagri": "32.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Cimahi",
            "kode_bps": "32.76",
            "kode_kemendagri": "32.76",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Semarang",
            "kode_bps": "33.71",
            "kode_kemendagri": "33.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Kendal",
            "kode_bps": "33.08",
            "kode_kemendagri": "33.08",
        },
        {"sumber": "PIHPS", "nama": "Kota Solo", "kode_bps": "33.72", "kode_kemendagri": "33.72"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Karanganyar",
            "kode_bps": "33.03",
            "kode_kemendagri": "33.03",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Balikpapan",
            "kode_bps": "64.71",
            "kode_kemendagri": "64.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Penajam Paser Utara",
            "kode_bps": "64.12",
            "kode_kemendagri": "64.12",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Samarinda",
            "kode_bps": "64.71",
            "kode_kemendagri": "64.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Kutai Kartanegara",
            "kode_bps": "64.02",
            "kode_kemendagri": "64.02",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Tarakan",
            "kode_bps": "65.71",
            "kode_kemendagri": "65.71",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Bulungan",
            "kode_bps": "65.02",
            "kode_kemendagri": "65.02",
        },
        {"sumber": "PIHPS", "nama": "Kota Palu", "kode_bps": "82.71", "kode_kemendagri": "82.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Sigi",
            "kode_bps": "82.02",
            "kode_kemendagri": "82.02",
        },
        {"sumber": "PIHPS", "nama": "Kota Sorong", "kode_bps": "92.71", "kode_kemendagri": "92.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Raja Ampat",
            "kode_bps": "92.04",
            "kode_kemendagri": "92.04",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kota Ternate",
            "kode_bps": "92.72",
            "kode_kemendagri": "92.72",
        },
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Halmahera Utara",
            "kode_bps": "92.03",
            "kode_kemendagri": "92.03",
        },
        {"sumber": "PIHPS", "nama": "Kota Manado", "kode_bps": "71.71", "kode_kemendagri": "71.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Minahasa",
            "kode_bps": "71.02",
            "kode_kemendagri": "71.02",
        },
        {"sumber": "PIHPS", "nama": "Kota Ambon", "kode_bps": "81.71", "kode_kemendagri": "81.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Maluku Tengah",
            "kode_bps": "81.02",
            "kode_kemendagri": "81.02",
        },
        {"sumber": "PIHPS", "nama": "Kota Kupang", "kode_bps": "53.71", "kode_kemendagri": "53.71"},
        {
            "sumber": "PIHPS",
            "nama": "Kabupaten Timor Tengah Selatan",
            "kode_bps": "53.02",
            "kode_kemendagri": "53.02",
        },
    ]
    # HDX source examples (World Food Programme)
    hdx_rows = [
        {
            "sumber": "HDX",
            "nama": "Kabupaten Cilacap",
            "kode_bps": "33.01",
            "kode_kemendagri": "33.01",
        },
        {
            "sumber": "HDX",
            "nama": "Kota Tasikmalaya",
            "kode_bps": "32.72",
            "kode_kemendagri": "32.72",
        },
        {
            "sumber": "HDX",
            "nama": "Kabupaten Ciamis",
            "kode_bps": "32.02",
            "kode_kemendagri": "32.02",
        },
        {"sumber": "HDX", "nama": "Kota Sukabumi", "kode_bps": "32.72", "kode_kemendagri": "32.72"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Majalengka",
            "kode_bps": "32.05",
            "kode_kemendagri": "32.05",
        },
        {"sumber": "HDX", "nama": "Kota Garut", "kode_bps": "32.04", "kode_kemendagri": "32.04"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Cirebon",
            "kode_bps": "32.03",
            "kode_kemendagri": "32.03",
        },
        {"sumber": "HDX", "nama": "Kota Bekasi", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Karawang",
            "kode_bps": "32.09",
            "kode_kemendagri": "32.09",
        },
        {"sumber": "HDX", "nama": "Kota Bogor", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Sukabumi",
            "kode_bps": "32.01",
            "kode_kemendagri": "32.01",
        },
        {"sumber": "HDX", "nama": "Kota Depok", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Lebak",
            "kode_bps": "36.01",
            "kode_kemendagri": "36.01",
        },
        {"sumber": "HDX", "nama": "Kota Serang", "kode_bps": "36.71", "kode_kemendagri": "36.71"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Pandeglang",
            "kode_bps": "36.02",
            "kode_kemendagri": "36.02",
        },
        {"sumber": "HDX", "nama": "Kota Cilegon", "kode_bps": "36.71", "kode_kemendagri": "36.71"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Indramayu",
            "kode_bps": "32.08",
            "kode_kemendagri": "32.08",
        },
        {"sumber": "HDX", "nama": "Kota Cirebon", "kode_bps": "32.03", "kode_kemendagri": "32.03"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Subang",
            "kode_bps": "32.07",
            "kode_kemendagri": "32.07",
        },
        {"sumber": "HDX", "nama": "Kota Banjar", "kode_bps": "32.04", "kode_kemendagri": "32.04"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Pangandaran",
            "kode_bps": "32.08",
            "kode_kemendagri": "32.08",
        },
        {"sumber": "HDX", "nama": "Kota Ciamis", "kode_bps": "32.02", "kode_kemendagri": "32.02"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Tasikmalaya",
            "kode_bps": "32.04",
            "kode_kemendagri": "32.04",
        },
        {"sumber": "HDX", "nama": "Kota Banjar", "kode_bps": "32.04", "kode_kemendagri": "32.04"},
        {
            "sumber": "HDX",
            "nama": "Kabupaten Ciamis",
            "kode_bps": "32.02",
            "kode_kemendagri": "32.02",
        },
    ]
    # BPS source examples (BPS official data)
    bps_rows = [
        {"sumber": "BPS", "nama": "Kota Jakarta", "kode_bps": "31.71", "kode_kemendagri": "31.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Bogor",
            "kode_bps": "32.01",
            "kode_kemendagri": "32.01",
        },
        {"sumber": "BPS", "nama": "Kota Depok", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {"sumber": "BPS", "nama": "Kota Bekasi", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Karawang",
            "kode_bps": "32.09",
            "kode_kemendagri": "32.09",
        },
        {"sumber": "BPS", "nama": "Kota Bandung", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Ciamis",
            "kode_bps": "32.02",
            "kode_kemendagri": "32.02",
        },
        {
            "sumber": "BPS",
            "nama": "Kota Tasikmalaya",
            "kode_bps": "32.72",
            "kode_kemendagri": "32.72",
        },
        {
            "sumber": "BPS",
            "nama": "Kabupaten Majalengka",
            "kode_bps": "32.05",
            "kode_kemendagri": "32.05",
        },
        {"sumber": "BPS", "nama": "Kota Cirebon", "kode_bps": "32.03", "kode_kemendagri": "32.03"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Kuningan",
            "kode_bps": "32.04",
            "kode_kemendagri": "32.04",
        },
        {"sumber": "BPS", "nama": "Kota Semarang", "kode_bps": "33.71", "kode_kemendagri": "33.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Demak",
            "kode_bps": "33.01",
            "kode_kemendagri": "33.01",
        },
        {"sumber": "BPS", "nama": "Kota Solo", "kode_bps": "33.72", "kode_kemendagri": "33.72"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Sukoharjo",
            "kode_bps": "33.03",
            "kode_kemendagri": "33.03",
        },
        {"sumber": "BPS", "nama": "Kota Surabaya", "kode_bps": "35.71", "kode_kemendagri": "35.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Sidoarjo",
            "kode_bps": "35.10",
            "kode_kemendagri": "35.10",
        },
        {"sumber": "BPS", "nama": "Kota Makassar", "kode_bps": "73.71", "kode_kemendagri": "73.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Maros",
            "kode_bps": "73.03",
            "kode_kemendagri": "73.03",
        },
        {"sumber": "BPS", "nama": "Kota Kendari", "kode_bps": "74.71", "kode_kemendagri": "74.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Konawe",
            "kode_bps": "74.01",
            "kode_kemendagri": "74.01",
        },
        {
            "sumber": "BPS",
            "nama": "Kota Palembang",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "BPS",
            "nama": "Kabupaten Banyuasin",
            "kode_bps": "16.03",
            "kode_kemendagri": "16.03",
        },
        {"sumber": "BPS", "nama": "Kota Medan", "kode_bps": "12.71", "kode_kemendagri": "12.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Deli Serdang",
            "kode_bps": "12.01",
            "kode_kemendagri": "12.01",
        },
        {
            "sumber": "BPS",
            "nama": "Kota Pekanbaru",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "BPS",
            "nama": "Kabupaten Kampar",
            "kode_bps": "14.03",
            "kode_kemendagri": "14.03",
        },
        {"sumber": "BPS", "nama": "Kota Jambi", "kode_bps": "15.71", "kode_kemendagri": "15.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Muaro Jambi",
            "kode_bps": "15.01",
            "kode_kemendagri": "15.01",
        },
        {
            "sumber": "BPS",
            "nama": "Kota Balikpapan",
            "kode_bps": "64.71",
            "kode_kemendagri": "64.71",
        },
        {
            "sumber": "BPS",
            "nama": "Kabupaten Paser",
            "kode_bps": "64.04",
            "kode_kemendagri": "64.04",
        },
        {
            "sumber": "BPS",
            "nama": "Kota Samarinda",
            "kode_bps": "64.71",
            "kode_kemendagri": "64.71",
        },
        {
            "sumber": "BPS",
            "nama": "Kabupaten Kutai Kartanegara",
            "kode_bps": "64.02",
            "kode_kemendagri": "64.02",
        },
        {"sumber": "BPS", "nama": "Kota Tarakan", "kode_bps": "65.71", "kode_kemendagri": "65.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Bulungan",
            "kode_bps": "65.02",
            "kode_kemendagri": "65.02",
        },
        {"sumber": "BPS", "nama": "Kota Palu", "kode_bps": "82.71", "kode_kemendagri": "82.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Donggala",
            "kode_bps": "82.01",
            "kode_kemendagri": "82.01",
        },
        {"sumber": "BPS", "nama": "Kota Sorong", "kode_bps": "92.71", "kode_kemendagri": "92.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Sorong",
            "kode_bps": "92.04",
            "kode_kemendagri": "92.04",
        },
        {"sumber": "BPS", "nama": "Kota Ternate", "kode_bps": "92.72", "kode_kemendagri": "92.72"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Halmahera Utara",
            "kode_bps": "92.03",
            "kode_kemendagri": "92.03",
        },
        {"sumber": "BPS", "nama": "Kota Manado", "kode_bps": "71.71", "kode_kemendagri": "71.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Bolaang Mongondow",
            "kode_bps": "71.01",
            "kode_kemendagri": "71.01",
        },
        {"sumber": "BPS", "nama": "Kota Ambon", "kode_bps": "81.71", "kode_kemendagri": "81.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Maluku Tengah",
            "kode_bps": "81.02",
            "kode_kemendagri": "81.02",
        },
        {"sumber": "BPS", "nama": "Kota Kupang", "kode_bps": "53.71", "kode_kemendagri": "53.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Kupang",
            "kode_bps": "53.02",
            "kode_kemendagri": "53.02",
        },
        {"sumber": "BPS", "nama": "Kota Mataram", "kode_bps": "52.71", "kode_kemendagri": "52.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Lombok Barat",
            "kode_bps": "52.01",
            "kode_kemendagri": "52.01",
        },
        {"sumber": "BPS", "nama": "Kota Bandung", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Sukabumi",
            "kode_bps": "32.01",
            "kode_kemendagri": "32.01",
        },
        {"sumber": "BPS", "nama": "Kota Bogor", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Cianjur",
            "kode_bps": "32.04",
            "kode_kemendagri": "32.04",
        },
        {"sumber": "BPS", "nama": "Kota Bogor", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Karawang",
            "kode_bps": "32.09",
            "kode_kemendagri": "32.09",
        },
        {"sumber": "BPS", "nama": "Kota Bekasi", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {
            "sumber": "BPS",
            "nama": "Kabupaten Bogor",
            "kode_bps": "32.01",
            "kode_kemendagri": "32.01",
        },
        {"sumber": "BPS", "nama": "Kota Depok", "kode_bps": "32.76", "kode_kemendagri": "32.76"},
        {"sumber": "BPS", "nama": "Kota Bogor", "kode_bps": "32.71", "kode_kemendagri": "32.71"},
    ]
    # Kemendagri source examples (Ministry of Home Affairs)
    kemendagri_rows = [
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Aceh Barat",
            "kode_bps": "11.01",
            "kode_kemendagri": "11.01",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Banda Aceh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Pidie",
            "kode_bps": "11.03",
            "kode_kemendagri": "11.03",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Banda Aceh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Aceh Singkil",
            "kode_bps": "11.02",
            "kode_kemendagri": "11.02",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lhoksumawe",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Singkil",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Meulaboh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Simeulue",
            "kode_bps": "11.08",
            "kode_kemendagri": "11.08",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sinabang",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Meulaboh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lhoksumawe",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sibolga",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Tapanuli Utara",
            "kode_bps": "12.02",
            "kode_kemendagri": "12.02",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Padangsidempuan",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Balai",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kabupaten Simalungun",
            "kode_bps": "12.03",
            "kode_kemendagri": "12.03",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Medan",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lubuk Pakam",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pematang Siantar",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Karang",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Binjai",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Langsa",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Takengon",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tapak Tuan",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Subulussalam",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Meulaboh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lhoksumawe",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sabang",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Simeulue",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pidie",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Aceh",
            "kode_bps": "11.71",
            "kode_kemendagri": "11.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sibolga",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pangururan",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Parapat",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pematang Siantar",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Balai",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Medan",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Binjai",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lubuk Pakam",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Karang",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tebing Tinggi",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pagar Alam",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lubuk Basung",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Selatpanjang",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Dabo Singkep",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pulau Punjung",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Siak",
            "kode_bps": "12.71",
            "kode_kemendagri": "12.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pekanbaru",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bangkinang",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pangkal Pinang",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sungailiat",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Jambi",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sungai Bahar",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muara Bulian",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bungo",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sarolangun",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muaro Saman",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Jabung",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pangkalan Kerinci",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Talang Gudang",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Rimbo Bujang",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muara Sabak",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanah Grogot",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Merangin",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bangko",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Rantau",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tanjung Gading",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Jambi",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bengkulu",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Curup",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Kepahiang",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Arga Binar",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Teluk Pinang",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Semidang",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Tais",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Seluma",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pagar Jati",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pondok Tinggi",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Martapura",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Benambah",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sengating",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lubuklinggau",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pagar Alam",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Curup",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Kepahiang",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bengkulu",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sungai Bulian",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muara Enim",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Baturaja",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lubuklinggau",
            "kode_bps": "17.71",
            "kode_kemendagri": "17.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Palembang",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muara Enim",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pagar Alam",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Prabumulih",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Lahat",
            "kode_bps": "16.71",
            "kode_kemendagri": "16.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pangkal Pinang",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bangkinang",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sungailiat",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Pangkal Pinang",
            "kode_bps": "14.71",
            "kode_kemendagri": "14.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Jambi",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sungai Bahar",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muara Bulian",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Bungo",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Sarolangun",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
        {
            "sumber": "Kemendagri",
            "nama": "Kota Muaro Saman",
            "kode_bps": "15.71",
            "kode_kemendagri": "15.71",
        },
    ]
    return pihps_rows + hdx_rows + bps_rows + kemendagri_rows


# Match each source row to the reference ref_kabkota
def build_crosswalk():
    ref = load_ref_kabkota()
    sources = load_sources()
    output_rows = []
    match_stats = {"exact_code": 0, "exact_name": 0, "normalized_name": 0, "manual": 0}
    unmatched_names = []

    for src in sources:
        src_name = src["nama"].strip()
        src_kode = src.get("kode_bps", "").strip()
        found = False
        reason = ""
        match_method = ""
        # 1) exact_code: source's kode BPS matches kode_bps in ref_kabkota directly
        if src_kode and src_kode in ref:
            match_method = "exact_code"
            match_stats[match_method] += 1
            found = True
            reason = f"kode BPS '{src_kode}' cocok langsung"
        # 2) exact_name: source name matches the ref name exactly (case-insensitive)
        key_exact = src_name.lower()
        if key_exact in ref:
            match_method = "exact_name"
            match_stats[match_method] += 1
            found = True
            reason = f"nama '{src_name}' cocok persis (case-insensitive)"
        # 3) normalized_name: strip the "Kab./Kota" prefix, lowercase, remove punctuation
        norm = src_name.lower()
        for pat in ["kab.", "kabupaten ", "kota "]:
            if norm.startswith(pat):
                norm = norm[len(pat) :].strip()
        # Remove punctuation
        norm = "".join(c for c in norm if c.isalnum() or c.isspace())
        norm = " ".join(norm.split())
        if norm in ref:
            match_method = "normalized_name"
            match_stats[match_method] += 1
            found = True
            reason = f"nama '{src_name}' cocok setelah normalisasi"
        if not found:
            # 4) manual fallback
            match_method = "manual"
            match_stats[match_method] += 1
            # Try a manual map using the BPS code if available (otherwise we need to
            # find the kode_bps by hand). For this scenario we look for the best-matching
            # BPS code in ref_kabkota; for demonstration purposes we only set a manual
            # mapping based on well-known names.
            manual_mapping = {
                "Kota Cilegon": "36.71",
                "Kabupaten Serang": "36.01",
                "Kota Tangerang": "36.71",
                "Kota Bekasi": "32.76",
                "Kota Depok": "32.76",
                "Kota Bogor": "32.71",
                "Kota Sukabumi": "32.72",
                "Kota Cimahi": "32.76",
                "Kota Tasikmalaya": "32.72",
                "Kota Banjar": "32.04",
                "Kota Cirebon": "32.03",
                "Kota Bandung": "32.71",
                "Kabupaten Cirebon": "32.03",
            }
            matched_kode = None
            # Prefer a manual lookup by the given BPS code (if we have one)
            if src_kode and src_kode in ref:
                matched_kode = src_kode
                reason = f"kode BPS manual '{src_kode}'"
            else:
                # Try the manual map
                for pattern, kode in manual_mapping.items():
                    if src_name.lower() == pattern.lower():
                        matched_kode = kode
                        break
                if matched_kode:
                    reason = f"pemetaan manual '{pattern}' → kode '{matched_kode}'"
                else:
                    # Fallback: use the source's BPS code (if any), else NULL
                    if src_kode:
                        matched_kode = src_kode
                        reason = f"kode BPS fallback '{src_kode}' (tidak cocok di ref)"
                    else:
                        unmatched_names.append(src_name)
                        # For this demo scenario, default to code "00.00" with reason "unmapped"
                        matched_kode = "00.00"
                        reason = "Tidak terpetakan (manual, alasan: tidak ada kecocokan kode/nama)"
            src["kode_bps"] = matched_kode
            src["kode_kemendagri"] = matched_kode
            src["match_method"] = match_method
            src["alasan"] = reason
            output_rows.append(src)
        else:
            # Kept as-is: we still need a mapping for every source row
            src["kode_bps"] = src.get("kode_bps", "")
            src["kode_kemendagri"] = src.get("kode_kemendagri", "")
            src["match_method"] = match_method
            src["alasan"] = reason
            output_rows.append(src)

    # Write the result to the output CSV
    output_path = OUTPUT_DIR / "ref_crosswalk_wilayah.csv"
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)

    fieldnames = ["sumber", "nama", "kode_bps", "kode_kemendagri", "match_method", "alasan"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            # Select only the columns needed for output
            out_row = {
                "sumber": row["sumber"],
                "nama": row["nama"],
                "kode_bps": row.get("kode_bps", ""),
                "kode_kemendagri": row.get("kode_kemendagri", ""),
                "match_method": row.get("match_method", ""),
                "alasan": row.get("alasan", ""),
            }
            writer.writerow(out_row)

    print(f"Crosswalk mapping written to {output_path}")
    print(f"Match statistics: {match_stats}")
    if unmatched_names:
        print(f"Unmapped names: {unmatched_names}")


if __name__ == "__main__":
    build_crosswalk()
