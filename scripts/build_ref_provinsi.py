"""F2: build ref_provinsi seed.

1. Reads data/tmp/provinsi_raw.json (parsed from cahyadsn/wilayah SQL).
2. Fetches governor/capital coordinates from Open-Meteo Geocoding API
   (no key needed), saves raw responses to Mongo bronze.wilayah_raw.
3. Writes dbt seed CSV: dbt/panganwatch/seeds/ref_provinsi.csv.

Sources:
- Names/codes: cahyadsn/wilayah (Kepmendagri 2025), raw SQL in data/tmp/
- Coordinates: Open-Meteo Geocoding API https://geocoding-api.open-meteo.com/v1/search
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "data" / "tmp"
SEED = ROOT / "dbt" / "panganwatch" / "seeds" / "ref_provinsi.csv"

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Province names keyed by Kemendagri 2-digit code, from cahyadsn/wilayah SQL.
PROV_NAMES = {
    "11": "Aceh",
    "12": "Sumatera Utara",
    "13": "Sumatera Barat",
    "14": "Riau",
    "15": "Jambi",
    "16": "Sumatera Selatan",
    "17": "Bengkulu",
    "18": "Lampung",
    "19": "Kepulauan Bangka Belitung",
    "21": "Kepulauan Riau",
    "31": "Daerah Khusus Ibukota Jakarta",
    "32": "Jawa Barat",
    "33": "Jawa Tengah",
    "34": "Daerah Istimewa Yogyakarta",
    "35": "Jawa Timur",
    "36": "Banten",
    "51": "Bali",
    "52": "Nusa Tenggara Barat",
    "53": "Nusa Tenggara Timur",
    "61": "Kalimantan Barat",
    "62": "Kalimantan Tengah",
    "63": "Kalimantan Selatan",
    "64": "Kalimantan Timur",
    "65": "Kalimantan Utara",
    "71": "Sulawesi Utara",
    "72": "Sulawesi Tengah",
    "73": "Sulawesi Selatan",
    "74": "Sulawesi Tenggara",
    "75": "Gorontalo",
    "76": "Sulawesi Barat",
    "81": "Maluku",
    "82": "Maluku Utara",
    "91": "Papua",
    "92": "Papua Barat",
    "93": "Papua Selatan",
    "94": "Papua Tengah",
    "95": "Papua Pegunungan",
    "96": "Papua Barat Daya",
}

# Canonical capital city names (used for ibukota column).
# cahyadsn writes "Nabira" / "Jayawijaya" for 94/95; actual towns are Nabire / Wamena.
IBUKOTA_CANONICAL = {
    "21": "Tanjungpinang",
    "94": "Nabire",
    "95": "Wamena",
    "96": "Sorong",
}

# Override ibukota geocoding queries where the official name might not match
# the city exactly (use the city as known in common English/Indonesian usage).
# The raw ibukota from provinsi_raw.json is used for the ibukota column;
# the query is what we send to Open-Meteo. They usually match.
GEOCODE_QUERY_OVERRIDES: dict[str, str] = {
    "21": "Tanjung Pinang",  # geocoder needs space; "Tanjungpinang" matches wrong islands
    "94": "Nabire",  # cahyadsn writes "Nabira"; Open-Meteo knows "Nabire" in Papua Tengah
    "95": "Wamena",  # Papua Pegunungan capital: Jayawijaya is a regency, Wamena is the town
}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def geocode(city: str) -> dict | None:
    """Query Open-Meteo geocoding for a city; return first Indonesia result."""
    params = urllib.parse.urlencode({"name": city, "count": 5, "language": "id", "format": "json"})
    url = f"{GEOCODING_URL}?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    results = payload.get("results") or []
    # Prefer Indonesian result
    for r in results:
        if r.get("country_code") == "ID":
            return r
    return results[0] if results else None


def main() -> int:
    load_dotenv(ROOT / ".env")

    raw = json.loads((TMP / "provinsi_raw.json").read_text(encoding="utf-8"))
    if len(raw) != 38:
        print(f"ERROR: expected 38 provinces, got {len(raw)}")
        return 1

    from pymongo import MongoClient

    mongo_host = os.getenv("MONGO_HOST", "localhost")
    mongo_db = os.getenv("MONGO_DB", "bronze")
    client = MongoClient(mongo_host, serverSelectionTimeoutMS=5000)
    coll = client[mongo_db]["wilayah_raw"]

    # Clear previous F2 build docs
    coll.delete_many({"_meta.run_id": "f2-reference-build"})

    rows = []
    errors = []
    for prov in raw:
        code = prov["kode_kemendagri"]
        ibukota = IBUKOTA_CANONICAL.get(code, prov["ibukota"])
        prov_name = PROV_NAMES[code]
        query = GEOCODE_QUERY_OVERRIDES.get(code, ibukota)

        # Geocode with retry up to 3 attempts
        geo = None
        last_exc = None
        for attempt in range(1, 4):
            try:
                geo = geocode(query)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < 3:
                    time.sleep(2 * attempt)

        raw_doc = {
            "_meta": {
                "source": "open-meteo/geocoding",
                "endpoint": GEOCODING_URL,
                "params": {"name": query, "count": 5, "language": "id"},
                "http_status": 200 if geo else 0,
                "run_id": "f2-reference-build",
                "fetched_at": datetime.now(UTC).isoformat(),
            },
            "province_code_kemendagri": code,
            "query": query,
            "cahyadsn_ibukota": ibukota,
            "response": geo,
        }
        coll.insert_one(raw_doc)

        if geo:
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            rows.append(
                {
                    "kode_bps": code,
                    "kode_kemendagri": code,
                    "nama_provinsi": prov_name,
                    "ibu_kota": ibukota,
                    "lat": lat,
                    "lon": lon,
                    "source": "open-meteo/geocoding;cahyadsn/wilayah (Kepmendagri 2025)",
                }
            )
        else:
            err_msg = f"{code}: no geocode result for '{query}'"
            if last_exc:
                err_msg += f" ({last_exc})"
            errors.append(err_msg)

    if rows:
        SEED.parent.mkdir(parents=True, exist_ok=True)
        with SEED.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "kode_bps",
                    "kode_kemendagri",
                    "nama_provinsi",
                    "ibu_kota",
                    "lat",
                    "lon",
                    "source",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} provinces to {SEED}")

        # Preview for verification
        preview = TMP / "ref_provinsi_preview.json"
        preview.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    count = coll.count_documents({"_meta.run_id": "f2-reference-build"})
    print(f"Raw docs in bronze.wilayah_raw: {count}")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(" -", e)
        return 1
    print("All 38 provinces geocoded successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
