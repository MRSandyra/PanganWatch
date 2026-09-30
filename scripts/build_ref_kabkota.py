"""Parse kab/kota rows from cahyadsn/wilayah SQL dump (level 2).

Reads data/tmp/wilayah_level.sql, extracts rows with kode containing '.'
(province.kabupaten format), writes dbt/panganwatch/seeds/ref_kabkota.csv.
"""

import csv
import json
import re
from pathlib import Path

SQL_PATH = Path("data/tmp/wilayah_level.sql")
OUT_CSV = Path("dbt/panganwatch/seeds/ref_kabkota.csv")
OUT_JSON = Path("data/tmp/ref_kabkota_raw.json")

sql = SQL_PATH.read_text(encoding="utf-8")

rows = []
# Each INSERT row: ('11.01','Aceh Selatan','Tapak Tuan', lat, lng, ...)
# Pattern: ^('kode','nama','ibukota', lat, lng, ...
pattern = re.compile(
    r"^\('([^']+)','([^']+)','([^']+)',\s*(-?[\d.]+),\s*(-?[\d.]+)",
    re.M,
)
for m in pattern.finditer(sql):
    kode, nama, ibukota, lat, lng = m.groups()
    rows.append(
        {
            "kode": kode,
            "nama": nama,
            "ibukota": ibukota,
            "lat": float(lat),
            "lng": float(lng),
        }
    )

# Deduplicate (multiple INSERT chunks)
seen = set()
unique = []
for r in rows:
    if r["kode"] not in seen:
        seen.add(r["kode"])
        unique.append(r)

# Filter kab/kota: kode contains '.' (e.g., '11.01', '31.71')
kabkota = [r for r in unique if "." in r["kode"]]
kabkota.sort(key=lambda x: x["kode"])

print(f"total unique rows: {len(unique)}")
print(f"kab/kota: {len(kabkota)}")

# Build dbt seed rows
seed_rows = []
for r in kabkota:
    kode_full = r["kode"]
    kode_provinsi = kode_full.split(".")[0]  # '11' from '11.01'
    seed_rows.append(
        {
            "kode_bps": kode_full,
            "kode_kemendagri": kode_full,
            "kode_provinsi_bps": kode_provinsi,
            "nama": r["nama"],
        }
    )

# Write CSV
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["kode_bps", "kode_kemendagri", "kode_provinsi_bps", "nama"],
    )
    writer.writeheader()
    writer.writerows(seed_rows)

# Write raw for provenance
OUT_JSON.write_text(json.dumps(kabkota, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Wrote {len(seed_rows)} kab/kota to {OUT_CSV}")
