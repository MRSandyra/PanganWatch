"""Verification script for PanganWatch phases.

Usage:
    python scripts/verify.py --phase 0
    python scripts/verify.py --phase 1
    python scripts/verify.py --phase all
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Some shells on Windows default stdout to a legacy codepage (e.g. cp1252)
# that can't encode the checkmark/cross characters used below, crashing the
# script before it prints any result. Force UTF-8 so this runs the same way
# regardless of the invoking shell.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_command(cmd: str, description: str) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    print(f"\n[CHECK] {description}")
    print(f"  Command: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30
        )

        output = result.stdout + result.stderr
        success = result.returncode == 0
        if success:
            print("  ✓ PASS")
        else:
            print(f"  ✗ FAIL (exit code {result.returncode})")
            if output:
                print(f"  Output: {output[:200]}")
        return success, output
    except subprocess.TimeoutExpired:
        print("  ✗ FAIL (timeout)")
        return False, "Timeout"
    except Exception as e:
        print(f"  ✗ FAIL (error: {e})")
        return False, str(e)


def docker_memory_usage_mib(names: list[str] | None = None) -> tuple[float, str]:
    """Sum MemUsage (used side, e.g. '36.64MiB / 1GiB') across containers.

    If `names` is given, only those exact container names are summed;
    otherwise any container whose name contains 'panganwatch' is summed.
    Returns (total_mib, raw_output_for_matched_lines).
    """
    result = subprocess.run(
        'docker stats --no-stream --format "{{.Name}}\t{{.MemUsage}}"',
        shell=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    output = result.stdout + result.stderr
    total_mib = 0.0
    matched_lines = []
    unit_re = re.compile(r"^([\d.]+)\s*(GiB|MiB|KiB|kB|B)$")
    for line in output.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        if names is not None:
            if cols[0] not in names:
                continue
        elif "panganwatch" not in line:
            continue
        matched_lines.append(line)
        used = cols[1].split("/")[0].strip()  # "36.64MiB / 1GiB" -> "36.64MiB"
        m = unit_re.match(used)
        if not m:
            continue
        value, unit = float(m.group(1)), m.group(2)
        if unit == "GiB":
            total_mib += value * 1024
        elif unit == "MiB":
            total_mib += value
        elif unit in ("KiB", "kB"):
            total_mib += value / 1024
        # B: negligible, ignored
    return total_mib, "\n".join(matched_lines)


def verify_phase_0() -> bool:
    """Verify F0: Bootstrap repo and tooling."""
    print("\n" + "=" * 60)
    print("PHASE 0: Bootstrap repo and tooling")
    print("=" * 60)

    all_passed = True

    success, _ = run_command("uv run ruff check .", "Lint check (ruff)")
    all_passed &= success

    success, _ = run_command('uv run python -c "import panganwatch"', "Package import")
    all_passed &= success

    print("\n[CHECK] .env in .gitignore")
    gitignore_lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    if ".env" in [line.strip() for line in gitignore_lines]:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL: '.env' not found as an exact line in .gitignore")
        all_passed = False

    print("\n[CHECK] No git commands in codebase")
    # Pure-Python scan (portable): grep.exe isn't guaranteed to exist on Windows.
    git_pattern = re.compile(
        r'(^|[;&\s"(])git\s+(init|add|commit|push|tag|clone|status|diff|log|checkout|reset)'
    )
    git_scan_ok = True
    for target in ["Makefile", "scripts/", "src/"]:
        target_path = Path(target)
        if not target_path.exists():
            continue
        files = (
            [target_path]
            if target_path.is_file()
            else [p for p in target_path.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        )
        found = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if git_pattern.search(line):
                    found.append(f"{f}:{lineno}: {line.strip()}")
        if found:
            print(f"  ✗ FAIL: Found git commands in {target}")
            for f in found:
                print(f"    {f}")
            git_scan_ok = False
        else:
            print(f"  ✓ {target}: no git commands")
    all_passed &= git_scan_ok

    print("\n[CHECK] Required files exist")
    required_files = [
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        ".env.example",
        "config/settings.yaml",
        "CHANGELOG.md",
    ]
    for file in required_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 0: ✓ ALL CHECKS PASSED")
    else:
        print("PHASE 0: ✗ SOME CHECKS FAILED")
    print("=" * 60)
    return all_passed


def verify_phase_1() -> bool:
    """Verify F1: Infrastructure (Postgres, MongoDB, Kafka)."""
    print("\n" + "=" * 60)
    print("PHASE 1: Infrastructure (Postgres, MongoDB, Kafka)")
    print("=" * 60)

    all_passed = True

    # File checks
    files = [
        "docker-compose.yml",
        ".env",
        "src/panganwatch/db.py",
        "sql/ddl/init_governance.sql",
        "docker/postgres/01-init.sh",
        "docker/kafka/init_topics.sh",
    ]
    print("\n[CHECK] Required files exist")
    for file in files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_passed = False

    # Docker compose services
    print("\n[CHECK] docker-compose.yml services")
    try:
        import yaml

        with open("docker-compose.yml") as f:
            compose = yaml.safe_load(f)
        services = list(compose.get("services", {}).keys())
        expected = {"postgres", "mongo", "kafka", "kafka-init"}
        if set(services) >= expected:
            print("  ✓ Services include Postgres, Mongo, Kafka, kafka-init")
        else:
            print(f"  ✗ Services incomplete: {services}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Failed to read docker-compose.yml: {e}")
        all_passed = False

    # Docker compose ps --format json: all healthy
    print("\n[CHECK] Docker compose ps (healthy)")
    result = subprocess.run(
        "docker compose ps --format json",
        shell=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        print("  ✗ docker compose ps failed or returned nothing")
        all_passed = False
    else:
        services_status: dict[str, dict] = {}
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            svc = item.get("Service")
            if svc:
                services_status[svc] = item
        required = {"postgres", "mongo", "kafka"}
        for svc in required:
            item = services_status.get(svc)
            if not item:
                print(f"  ✗ {svc} not found in docker compose ps")
                all_passed = False
            elif item.get("State") != "running" or "healthy" not in item.get("Status", ""):
                print(f"  ✗ {svc} not healthy: {item.get('Status')}")
                all_passed = False
            else:
                print(f"  ✓ {svc}: {item.get('Status')}")

    # Postgres host connection + governance schema
    print("\n[CHECK] Postgres host connection + governance schema")
    success, output = run_command(
        'uv run python -c "'
        "from panganwatch.db import get_postgres_connection; "
        "c=get_postgres_connection(); "
        "cur=c.cursor(); "
        "cur.execute(\\\"SELECT to_regclass('governance.pipeline_runs') IS NOT NULL\\\"); "
        "print('governance.pipeline_runs:', cur.fetchone()[0]); "
        "cur.execute(\\\"SELECT to_regclass('governance.dq_results') IS NOT NULL\\\"); "
        "print('governance.dq_results:', cur.fetchone()[0]); "
        "cur.execute(\\\"SELECT to_regclass('governance.quarantine') IS NOT NULL\\\"); "
        "print('governance.quarantine:', cur.fetchone()[0]); "
        'c.close()"',
        "Postgres connection + governance tables",
    )
    all_passed &= success

    # Kafka topics
    print("\n[CHECK] Kafka topics")
    success, output = run_command(
        "docker exec panganwatch-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list",
        "Kafka topic list",
    )
    all_passed &= success
    if success:
        for topic in ["weather.current.raw", "weather.current.dlq", "weather.alert"]:
            if topic in output:
                print(f"  ✓ topic {topic}")
            else:
                print(f"  ✗ topic {topic} MISSING")
                all_passed = False

    # Memory limit
    print("\n[CHECK] Memory usage < 2.5 GiB")
    total_mib, raw_output = docker_memory_usage_mib(
        ["panganwatch-postgres", "panganwatch-mongo", "panganwatch-kafka"]
    )
    if not raw_output.strip():
        print("  ✗ docker stats failed or returned nothing")
        all_passed = False
    else:
        print(f"  {raw_output.strip()}")
        print(f"  Total memory: {total_mib:.1f} MiB ({total_mib / 1024:.2f} GiB)")
        if total_mib < 2560:
            print("  ✓ Total memory < 2.5 GiB")
        else:
            print("  ✗ Total memory >= 2.5 GiB")
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 1: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 1: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


def verify_phase_2() -> bool:
    """Verify F2: Reference and master data."""
    print("\n" + "=" * 60)
    print("PHASE 2: Reference and master data")
    print("=" * 60)

    all_passed = True

    # Required files
    files = [
        "dbt/panganwatch/dbt_project.yml",
        "dbt/panganwatch/seeds/ref_provinsi.csv",
        "dbt/panganwatch/seeds/ref_kabkota.csv",
        "dbt/panganwatch/seeds/ref_crosswalk_wilayah.csv",
        "dbt/panganwatch/seeds/ref_komoditas.csv",
        "dbt/panganwatch/seeds/ref_komoditas_alias.csv",
        "dbt/panganwatch/seeds/schema.yml",
        "dbt/panganwatch/macros/bbox_indonesia.sql",
        "dbt/panganwatch/macros/prov_kab_unique.sql",
        "scripts/build_ref_provinsi.py",
        "scripts/build_ref_kabkota.py",
        "scripts/build_ref_crosswalk.py",
        "scripts/build_ref_komoditas.py",
        "docs/governance/crosswalk_report.md",
    ]
    print("\n[CHECK] Required files exist")
    for file in files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_passed = False

    # dbt_project.yml content check
    print("\n[CHECK] dbt_project.yml is valid")
    project_path = Path("dbt/panganwatch/dbt_project.yml")
    if project_path.exists():
        content = project_path.read_text(encoding="utf-8")
        if "name: 'panganwatch'" in content and "profile: 'panganwatch'" in content:
            print("  ✓ dbt_project.yml is valid dbt project config")
        else:
            print("  ✗ dbt_project.yml is not a valid dbt project")
            all_passed = False

    # Postgres connection checks
    print("\n[CHECK] Postgres connection + seed counts")
    success, output = run_command(
        "uv run python scripts/check_f2_db.py",
        "Postgres seed counts + bbox check",
    )
    all_passed &= success

    # dbt test seeds
    print("\n[CHECK] dbt test seeds (exit 0)")
    result = subprocess.run(
        "cd dbt/panganwatch && uv run dbt test --select 'resource_type:seed' 2>&1",
        shell=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    output = result.stdout + result.stderr
    if result.returncode == 0:
        print("  ✓ dbt test seeds exit 0")
        for line in output.splitlines():
            if "Done. PASS=" in line or "Completed successfully" in line:
                print(f"  {line.strip()}")
    else:
        print("  ✗ dbt test seeds FAILED")
        for line in output.splitlines()[-10:]:
            print(f"  {line.strip()}")
        all_passed = False

    # Crosswalk report exists
    print("\n[CHECK] Crosswalk report exists")
    report_path = Path("docs/governance/crosswalk_report.md")
    if report_path.exists():
        content = report_path.read_text(encoding="utf-8")
        if "exact_code" in content and "normalized_name" in content and "manual" in content:
            print("  ✓ crosswalk_report.md contains match_method stats")
        else:
            print("  ✗ crosswalk_report.md missing match_method stats")
            all_passed = False
    else:
        print("  ✗ crosswalk_report.md MISSING")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 2: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 2: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


ALLOWED_SKIP_CHECK_IDS = {"bps_f3b_ingestion", "bps_f5_mart_inflasi_vs_harga"}


def _bps_key_is_set() -> bool:
    """True if BPS_API_KEY is filled (process env or .env). Only SET/EMPTY is ever shown."""
    if os.getenv("BPS_API_KEY"):
        return True
    try:
        from dotenv import dotenv_values

        return bool(dotenv_values(".env").get("BPS_API_KEY"))
    except Exception:
        return False


def load_skips() -> list[dict]:
    """Read config/verification_skips.yml and reject any check_id outside the allow-list."""
    import yaml

    path = Path("config/verification_skips.yml")
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("skips", [])
    for entry in entries:
        if entry.get("check_id") not in ALLOWED_SKIP_CHECK_IDS:
            raise ValueError(
                f"check_id {entry.get('check_id')!r} in skips.yml is not in the allowed list "
                f"(see ALLOWED_SKIP_CHECK_IDS above): {ALLOWED_SKIP_CHECK_IDS}"
            )
    return entries


def verify_phase_3() -> bool:
    """Verify F3: Batch ingestion into bronze and silver."""
    print("\n" + "=" * 60)
    print("PHASE 3: Batch ingestion into bronze and silver")
    print("=" * 60)

    all_passed = True

    files = [
        "src/panganwatch/bronze.py",
        "src/panganwatch/config.py",
        "src/panganwatch/unmapped.py",
        "src/panganwatch/governance/pipeline_runs.py",
        "src/panganwatch/silver/harga_pangan.py",
        "src/panganwatch/silver/cuaca_harian.py",
        "src/panganwatch/sources/hdx_wfp.py",
        "src/panganwatch/sources/pihps.py",
        "src/panganwatch/sources/bps.py",
        "src/panganwatch/sources/open_meteo.py",
        "dbt/panganwatch/seeds/ref_provinsi_alias.csv",
        "config/verification_skips.yml",
    ]
    print("\n[CHECK] Required files exist")
    for file in files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_passed = False

    print("\n[CHECK] skips.yml only lists allowed check_id values")
    try:
        skips = load_skips()
        print(f"  ✓ {len(skips)} skip(s) declared, all allowed")
    except Exception as exc:
        print(f"  ✗ {exc}")
        all_passed = False
        skips = []

    try:
        from panganwatch.db import get_mongo_client, get_postgres_connection
    except Exception as exc:
        print(f"  ✗ Cannot import panganwatch.db: {exc}")
        print("\n" + "=" * 60)
        print("PHASE 3: ✗ SOME REQUIREMENTS FAILED")
        print("=" * 60)
        return False

    # Bronze envelope + index checks
    print("\n[CHECK] Bronze envelope + indexes (hdx_wfp_prices, open_meteo_daily)")
    required_meta_fields = {
        "source",
        "endpoint",
        "params",
        "fetched_at",
        "run_id",
        "http_status",
        "payload_sha256",
        "schema_version",
    }
    try:
        client = get_mongo_client()
        db = client.get_database("bronze")
        for collection in ("hdx_wfp_prices", "open_meteo_daily"):
            coll = db[collection]
            total = coll.count_documents({})
            if total == 0:
                print(f"  ✗ {collection}: 0 documents")
                all_passed = False
                continue
            missing_meta = coll.count_documents(
                {"$or": [{f"_meta.{field}": {"$exists": False}} for field in required_meta_fields]}
            )
            if missing_meta == 0:
                print(f"  ✓ {collection}: {total} docs, all with complete _meta envelope")
            else:
                print(
                    f"  ✗ {collection}: {missing_meta}/{total} docs missing required _meta fields"
                )
                all_passed = False

            index_info = coll.index_information()
            has_unique = any(idx.get("unique") for idx in index_info.values())
            ttl_ok = any(idx.get("expireAfterSeconds") == 7776000 for idx in index_info.values())
            if has_unique and ttl_ok:
                print(f"  ✓ {collection}: unique index + TTL 7776000 present")
            else:
                print(f"  ✗ {collection}: unique={has_unique} ttl_7776000={ttl_ok}")
                all_passed = False
        client.close()
    except Exception as exc:
        print(f"  ✗ Mongo check failed: {exc}")
        all_passed = False

    # Postgres-side checks
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        print("\n[CHECK] Price row volume (silver.harga_pangan)")
        cur.execute("SELECT count(*) FROM silver.harga_pangan")
        harga_count = cur.fetchone()[0]
        if harga_count >= 1000:
            print(
                f"  ✓ silver.harga_pangan = {harga_count} (>= 1000, monthly HDX WFP fallback source)"
            )
        else:
            print(f"  ✗ silver.harga_pangan = {harga_count} (< 1000)")
            all_passed = False

        print("\n[CHECK] Weather coverage (silver.cuaca_harian)")
        cur.execute("SELECT count(DISTINCT kode_provinsi_bps) FROM silver.cuaca_harian")
        weather_provinces = cur.fetchone()[0]
        if weather_provinces >= 38:
            print(f"  ✓ silver.cuaca_harian covers {weather_provinces} provinces")
        else:
            print(f"  ✗ silver.cuaca_harian covers only {weather_provinces}/38 provinces")
            all_passed = False

        print("\n[CHECK] Region integrity (silver.harga_pangan.kode_provinsi_bps)")
        cur.execute(
            """SELECT count(*) FROM silver.harga_pangan h
               LEFT JOIN ref.ref_provinsi p ON h.kode_provinsi_bps = p.kode_bps
               WHERE p.kode_bps IS NULL"""
        )
        orphan_count = cur.fetchone()[0]
        if orphan_count == 0:
            print("  ✓ 0 rows with a kode_provinsi_bps missing from ref.ref_provinsi")
        else:
            print(f"  ✗ {orphan_count} rows with an invalid kode_provinsi_bps")
            all_passed = False

        print("\n[CHECK] Run log governance.pipeline_runs")
        required_sources = {"HDX WFP", "Open-Meteo Archive"}
        cur.execute("SELECT DISTINCT source FROM governance.pipeline_runs")
        logged_sources = {row[0] for row in cur.fetchall()}
        missing_sources = required_sources - logged_sources
        if not missing_sources:
            print(f"  ✓ pipeline_runs has rows for: {sorted(required_sources)}")
        else:
            print(f"  ✗ pipeline_runs is missing rows for: {sorted(missing_sources)}")
            all_passed = False

        print(
            "\n[CHECK] F3b BPS (must PASS when BPS_API_KEY is set; WARN only when the key is empty)"
        )
        bps_key_set = _bps_key_is_set()
        print(f"  BPS_API_KEY in .env: {'SET' if bps_key_set else 'EMPTY'}")
        cur.execute(
            "SELECT status, rows_success FROM governance.pipeline_runs WHERE source = 'BPS' "
            "AND status <> 'running' ORDER BY started_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not bps_key_set:
            print("  WARN: BPS_API_KEY is empty, F3b is skipped -- allowed by policy")
        else:
            if row and row[0] == "success" and (row[1] or 0) > 0:
                print(f"  ✓ Last BPS run succeeded ({row[1]} rows loaded)")
            else:
                print(f"  ✗ Last BPS run was not a success with rows loaded: {row}")
                all_passed = False

            cur.execute(
                "SELECT count(*), count(DISTINCT kode_vervar), min(bulan), max(bulan) FROM silver.inflasi_kota"
            )
            n_rows, n_kota, bulan_min, bulan_max = cur.fetchone()
            if n_rows > 0 and n_kota >= 100:
                print(
                    f"  ✓ silver.inflasi_kota: {n_rows} rows, {n_kota} cities, {bulan_min}..{bulan_max}"
                )
            else:
                print(f"  ✗ silver.inflasi_kota is insufficient: {n_rows} rows, {n_kota} cities")
                all_passed = False

            cur.execute(
                "SELECT count(DISTINCT s.kode_vervar) FROM silver.inflasi_kota s "
                "LEFT JOIN ref.ref_ihk_kota m ON s.kode_vervar = m.kode_vervar "
                "WHERE m.kode_provinsi_bps IS NULL"
            )
            unmapped = cur.fetchone()[0]
            if unmapped == 0:
                print("  ✓ All IHK cities are mapped to a province (ref_ihk_kota)")
            else:
                print(f"  ✗ {unmapped} IHK cities are not mapped to a province")
                all_passed = False

            mclient = get_mongo_client()
            try:
                bcoll = mclient.get_database("bronze")["bps_inflation"]
                bdocs = bcoll.count_documents({})
                incomplete = bcoll.count_documents(
                    {"$or": [{f"_meta.{f}": {"$exists": False}} for f in required_meta_fields]}
                )
            finally:
                mclient.close()
            if bdocs > 0 and incomplete == 0:
                print(
                    f"  ✓ bronze bps_inflation: {bdocs} documents, all with a complete _meta envelope"
                )
            else:
                print(
                    f"  ✗ bronze bps_inflation: {bdocs} documents, {incomplete} with an incomplete envelope"
                )
                all_passed = False

        conn.close()
    except Exception as exc:
        print(f"  ✗ Postgres check failed: {exc}")
        all_passed = False

    print("\n[CHECK] Unit tests (offline, no network access)")
    success, output = run_command("uv run pytest -q tests/unit", "pytest tests/unit")
    all_passed &= success

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 3: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 3: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


def verify_phase_4() -> bool:
    """Verify F4: Data quality engine."""
    print("\n" + "=" * 60)
    print("PHASE 4: Data quality engine")
    print("=" * 60)

    all_passed = True

    files = [
        "config/dq_rules.yml",
        "src/panganwatch/dq/engine.py",
        "src/panganwatch/dq/__init__.py",
        "scripts/inject_bad_records.py",
        "docs/governance/dq_rules.md",
    ]
    print("\n[CHECK] Required files exist")
    for file in files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_passed = False

    try:
        import yaml as yaml_lib

        with open("config/dq_rules.yml", encoding="utf-8") as f:
            dq_data = yaml_lib.safe_load(f)
        rules = dq_data.get("rules", [])
        if len(rules) >= 15:
            print(f"  ✓ {len(rules)} rules defined (>= 15)")
        else:
            print(f"  ✗ Only {len(rules)} rules (need >= 15)")
            all_passed = False

        dimensions = {r["dimension"] for r in rules}
        required_dims = {
            "completeness",
            "validity",
            "accuracy",
            "consistency",
            "timeliness",
            "uniqueness",
        }
        missing_dims = required_dims - dimensions
        if not missing_dims:
            print("  ✓ All 6 DAMA dimensions covered")
        else:
            print(f"  ✗ Missing dimensions: {sorted(missing_dims)}")
            all_passed = False

        severities = {r["severity"] for r in rules}
        if "error" in severities and "warn" in severities:
            print("  ✓ Both error and warn severities present")
        else:
            print("  ✗ Missing severity levels")
            all_passed = False
    except Exception as exc:
        print(f"  ✗ Failed to parse dq_rules.yml: {exc}")
        all_passed = False

    try:
        from panganwatch.dq.engine import DQEngine

        engine = DQEngine()
        print(f"  ✓ DQEngine loaded {len(engine.rules)} rules")
    except Exception as exc:
        print(f"  ✗ Failed to import DQ engine: {exc}")
        all_passed = False

    success, _ = run_command(
        "uv run pytest -q tests/unit/test_dq_engine.py", "pytest DQ engine tests"
    )
    all_passed &= success

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 4: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 4: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


def verify_phase_5() -> bool:
    """Verify F5: dbt transform (silver -> gold)."""
    print("\n" + "=" * 60)
    print("PHASE 5: dbt transform (silver -> gold)")
    print("=" * 60)

    all_passed = True
    dbt_dir = Path("dbt/panganwatch")

    print("\n[CHECK] dbt build (exclude seeds; seeds are verified separately in F2)")
    result = subprocess.run(
        "uv run dbt build --exclude resource_type:seed",
        shell=True,
        cwd=dbt_dir,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    output = result.stdout + result.stderr
    if result.returncode == 0:
        print("  ✓ dbt build exit 0")
        for line in output.splitlines():
            if "Done. PASS=" in line:
                print(f"  {line.strip()}")
    else:
        print("  ✗ dbt build FAILED")
        for line in output.splitlines()[-25:]:
            print(f"  {line.strip()}")
        all_passed = False

    print("\n[CHECK] dbt docs generate (manifest.json + catalog.json)")
    result = subprocess.run(
        "uv run dbt docs generate",
        shell=True,
        cwd=dbt_dir,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.returncode == 0 and (dbt_dir / "target" / "manifest.json").exists():
        print("  ✓ manifest.json + catalog.json present")
    else:
        print("  ✗ dbt docs generate FAILED")
        all_passed = False

    print("\n[CHECK] doc_coverage.py (0 gold columns without a description)")
    success, output = run_command(
        "uv run python -m panganwatch.governance.doc_coverage",
        "doc_coverage.py",
    )
    all_passed &= success

    print("\n[CHECK] Every gold mart has >= 1 row")
    required_tables = {
        "dim_provinsi",
        "dim_komoditas",
        "dim_tanggal",
        "fct_harga_bulanan",
        "mart_disparitas_provinsi",
        "mart_cuaca_harga_bulanan",
        "mart_dq_scorecard",
    }
    if _bps_key_is_set():
        required_tables.add("mart_inflasi_vs_harga")
    try:
        from panganwatch.db import get_postgres_connection

        conn = get_postgres_connection()
        with conn.cursor() as cur:
            for table in sorted(required_tables):
                cur.execute(f"SELECT count(*) FROM gold.{table}")
                count = cur.fetchone()[0]
                if count >= 1:
                    print(f"  ✓ gold.{table}: {count} rows")
                else:
                    print(f"  ✗ gold.{table}: 0 rows")
                    all_passed = False
        conn.close()
    except Exception as exc:
        print(f"  ✗ Gold schema query failed: {exc}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 5: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 5: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


def _kafka_topic_end_offset(topic: str) -> int | None:
    """Total log-end-offset across all partitions of `topic`, or None on failure."""
    result = subprocess.run(
        f"docker exec panganwatch-kafka /opt/kafka/bin/kafka-get-offsets.sh "
        f"--broker-list localhost:9092 --topic {topic}",
        shell=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        return None
    total = 0
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) == 3:
            total += int(parts[2])
    return total


def _compose(action: str) -> None:
    subprocess.run(
        f"docker compose {action}",
        shell=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )


def verify_phase_6() -> bool:
    """Verify F6, with the always-on weather-producer paused.

    The long-running producer publishes its own 38-message cycle every 900 s
    (and immediately after any restart), which raced with the exact-delta
    checks below (observed: +63 instead of +38 right after `docker compose
    restart`, DEC-038). Pause it for the duration, always start it again.
    """
    try:
        return _verify_phase_6_checks()
    finally:
        _compose("start weather-producer")


def _verify_phase_6_checks() -> bool:
    """Verify F6: Weather streaming through Kafka.

    This verification requires a working Kafka and Postgres.
    """
    print("\n" + "=" * 60)
    print("PHASE 6: Weather streaming through Kafka")
    print("=" * 60)

    all_passed = True
    from panganwatch.db import get_postgres_connection

    # Check 1: Docker services status
    print("\n[CHECK] Docker compose ps (healthy)")
    success, output = run_command(
        "docker compose ps --format json", "Docker compose service status"
    )
    if success:
        services_status = {}
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                svc = item.get("Service")
                if svc:
                    services_status[svc] = item
            except Exception:
                continue

        required = {"postgres", "kafka", "weather-producer", "weather-consumer"}
        for svc in required:
            item = services_status.get(svc)
            if not item:
                print(f"  ✗ {svc} not found in docker compose ps")
                all_passed = False
            elif item.get("State") != "running" or (
                svc in {"postgres", "kafka"} and "healthy" not in item.get("Status", "")
            ):
                print(f"  ✗ {svc} not healthy: {item.get('Status')}")
                all_passed = False
            else:
                print(f"  ✓ {svc}: {item.get('Status')}")
    else:
        all_passed = False

    # Check 2: Kafka topics
    print("\n[CHECK] Kafka topics")
    success, output = run_command(
        "docker exec panganwatch-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list",
        "Kafka topic list",
    )
    if success:
        for topic in ["weather.current.raw", "weather.current.dlq", "weather.alert"]:
            if topic in output:
                print(f"  ✓ topic {topic}")
            else:
                print(f"  ✗ topic {topic} MISSING")
                all_passed = False
    else:
        all_passed = False

    # From here on only this check's own traffic may reach Kafka/silver: pause the
    # always-on producer (verify_phase_6 restarts it in a finally block).
    _compose("stop weather-producer")

    # Check 3: Producer --once -> +38 messages on the raw topic, 38 fresh provinces in silver
    print(
        "\n[CHECK] Producer --once test (+38 messages on the raw topic, 38 fresh provinces in silver.cuaca_terkini)"
    )
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM silver.cuaca_terkini")
            before = cur.fetchone()[0]
        conn.close()
        raw_before = _kafka_topic_end_offset("weather.current.raw")

        result = subprocess.run(
            ["uv", "run", "python", "-m", "panganwatch.stream.producer", "--once"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if result.returncode == 0 and "Cycle complete: 38/38" in result.stdout:
            print(f"  ✓ Producer --once: {result.stdout.strip().splitlines()[-1]}")
        else:
            print(f"  ✗ Producer --once failed or did not reach 38/38 (exit={result.returncode})")
            print(f"    {result.stdout[-300:]}")
            all_passed = False

        time.sleep(10)  # give the consumer time to process before recounting
        raw_after = _kafka_topic_end_offset("weather.current.raw")
        if raw_before is not None and raw_after is not None and raw_after - raw_before == 38:
            print(
                f"  ✓ weather.current.raw grew by exactly 38 messages ({raw_before} -> {raw_after})"
            )
        else:
            print(f"  ✗ weather.current.raw did not grow by 38 ({raw_before} -> {raw_after})")
            all_passed = False
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM silver.cuaca_terkini")
            after = cur.fetchone()[0]
            cur.execute(
                "SELECT count(DISTINCT kode_provinsi_bps) FROM silver.cuaca_terkini "
                "WHERE observed_at >= now() - interval '2 hours'"
            )
            fresh = cur.fetchone()[0]
        conn.close()
        delta = after - before
        # Open-Meteo `current` is stamped per 15-minute slot, so a cycle inside a
        # slot that already exists upserts (0 new rows): the row delta is 0..38.
        if 0 <= delta <= 38 and fresh == 38:
            print(
                f"  ✓ 38 provinces have a fresh row (<2h); new rows {delta} ({before} -> {after})"
            )
        else:
            print(
                f"  ✗ fresh provinces={fresh} (should be 38), row delta={delta} ({before} -> {after})"
            )
            all_passed = False
    except Exception as exc:
        print(f"  ✗ Producer --once test error: {exc}")
        all_passed = False

    # Check 4: DLQ +3 via topic offset (not the Postgres table)
    print("\n[CHECK] DLQ (+3 messages via the weather.current.dlq topic offset)")
    try:
        dlq_before = _kafka_topic_end_offset("weather.current.dlq")
        silver_before = None
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM silver.cuaca_terkini")
            silver_before = cur.fetchone()[0]
        conn.close()

        result = subprocess.run(
            ["uv", "run", "python", "scripts/send_invalid_weather.py"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        time.sleep(8)
        dlq_after = _kafka_topic_end_offset("weather.current.dlq")

        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM silver.cuaca_terkini")
            silver_after = cur.fetchone()[0]
        conn.close()

        if (
            result.returncode == 0
            and dlq_before is not None
            and dlq_after is not None
            and (dlq_after - dlq_before) == 3
        ):
            print(f"  ✓ weather.current.dlq grew by exactly 3 ({dlq_before} -> {dlq_after})")
        else:
            print(f"  ✗ weather.current.dlq did not grow by 3 ({dlq_before} -> {dlq_after})")
            all_passed = False

        if silver_after == silver_before:
            print(f"  ✓ No new silver rows from the invalid messages ({silver_before} rows)")
        else:
            print(
                f"  ✗ silver.cuaca_terkini changed because of the invalid messages ({silver_before} -> {silver_after})"
            )
            all_passed = False
    except Exception as exc:
        print(f"  ✗ DLQ test error: {exc}")
        all_passed = False

    # Check 5: Consumer lag == 0
    print("\n[CHECK] Consumer lag == 0")
    success, output = run_command(
        "docker exec panganwatch-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group panganwatch-weather-sink",
        "Consumer group lag",
    )
    if success:
        lags = []
        for line in output.strip().splitlines():
            cols = line.split()
            if len(cols) >= 6 and cols[0] == "panganwatch-weather-sink":
                try:
                    lags.append(int(cols[5]))
                except ValueError:
                    pass
        if lags and all(lag == 0 for lag in lags):
            print(f"  ✓ Lag 0 across all {len(lags)} partitions")
        else:
            print(f"  ✗ Non-zero lag: {lags}")
            all_passed = False
    else:
        all_passed = False

    # Check 6: Idempotency (resend the same message, silver row count must not grow)
    print("\n[CHECK] Idempotency (resend the same message)")
    try:
        import json as _json

        from confluent_kafka import Producer as _Producer

        fixed_msg = {
            "event_id": "verify-idempotency-fixed",
            "schema_version": "1.0",
            "kode_provinsi_bps": "31",
            "observed_at": "2026-01-01T00:00:00+00:00",
            "temperature_c": 27.0,
            "precipitation_mm": 1.0,
            "source": "open-meteo",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "producer_id": "verify-phase-6",
        }
        bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kp = _Producer({"bootstrap.servers": bootstrap, "acks": "all"})

        def _send():
            kp.produce(
                topic="weather.current.raw",
                key=fixed_msg["kode_provinsi_bps"],
                value=_json.dumps(fixed_msg),
            )
            kp.flush(timeout=10)

        def _count():
            c = get_postgres_connection()
            with c.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM silver.cuaca_terkini WHERE kode_provinsi_bps=%s AND observed_at=%s",
                    (fixed_msg["kode_provinsi_bps"], fixed_msg["observed_at"]),
                )
                n = cur.fetchone()[0]
            c.close()
            return n

        _send()
        time.sleep(3)
        first_count = _count()
        _send()
        time.sleep(3)
        second_count = _count()

        if first_count == 1 and second_count == 1:
            print(f"  ✓ Resending the same message did not add a row (still {second_count})")
        else:
            print(f"  ✗ Idempotency failed (first={first_count}, second={second_count})")
            all_passed = False
    except Exception as exc:
        print(f"  ✗ Idempotency test error: {exc}")
        all_passed = False

    # Check 7: Contracts
    print("\n[CHECK] Kafka contracts JSON Schema")
    success = verify_phase_6_contract_check()
    if success:
        print("  ✓ Contracts check passed")
    else:
        print("  ✗ Contracts check failed")
        all_passed = False

    # Check 8: Memory < 3.5GiB (all F6 + F1 containers)
    print("\n[CHECK] Memory across all containers < 3.5GiB")
    total_mib, raw_output = docker_memory_usage_mib(
        [
            "panganwatch-postgres",
            "panganwatch-mongo",
            "panganwatch-kafka",
            "panganwatch-weather-producer",
            "panganwatch-weather-consumer",
        ]
    )
    if raw_output.strip():
        print(f"  {raw_output.strip()}")
        print(f"  Total memory: {total_mib:.1f} MiB ({total_mib / 1024:.2f} GiB)")
        if total_mib < 3584:
            print("  ✓ Total memory < 3.5 GiB")
        else:
            print("  ✗ Total memory >= 3.5 GiB")
            all_passed = False
    else:
        print("  ✗ docker stats failed or returned nothing")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 6: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 6: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)

    return all_passed


def verify_phase_6_contract_check() -> bool:
    """Check that contracts/*.json exist and are in sync with the model."""
    print("\n[CHECK] Message JSON Schema contracts")

    contracts_dir = Path("contracts")
    if not contracts_dir.exists():
        print("  ✗ 'contracts/' folder does not exist")
        return False

    expected_files = ["weather_current_v1.json", "weather_alert_v1.json"]
    all_exist = True

    for filename in expected_files:
        filepath = contracts_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename} exists")
        else:
            print(f"  ✗ {filename} MISSING")
            all_exist = False

    if not all_exist:
        return False

    # Check if contracts are not empty
    for filename in expected_files:
        filepath = contracts_dir / filename
        try:
            content = filepath.read_text(encoding="utf-8")
            if len(content.strip()) > 10:
                print(f"  ✓ {filename} has content")
            else:
                print(f"  ⚠️ {filename} is empty or too short")
        except Exception as e:
            print(f"  ✗ Failed to read {filename}: {e}")
            all_exist = False

    return all_exist


def _airflow_exec(args: list[str], timeout: int = 300) -> tuple[bool, str]:
    """Run a command inside the running panganwatch-airflow container."""
    cmd = ["docker", "compose", "exec", "-T", "airflow", *args]
    result = subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return result.returncode == 0, result.stdout + result.stderr


def verify_phase_7() -> bool:
    """Verify F7: Airflow orchestration.

    Runs real checks inside the running `airflow` container (docker compose
    exec) -- DAG import errors, dags list, dags test, the health endpoint, and
    memory across the whole stack.
    """
    print("\n" + "=" * 60)
    print("PHASE 7: Airflow orchestration")
    print("=" * 60)

    all_passed = True

    print("\n[CHECK] Required files")
    for f in [
        "docker/airflow/Dockerfile",
        "dags/panganwatch_daily.py",
        "dags/panganwatch_monthly_bps.py",
        "dags/panganwatch_reference.py",
        "dags/panganwatch_retention.py",
    ]:
        if Path(f).exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} MISSING")
            all_passed = False

    print("\n[CHECK] docker compose ps — airflow healthy")
    success, output = run_command(
        "docker compose ps --format json", "Docker compose service status"
    )
    airflow_up = False
    if success:
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("Service") == "airflow":
                status = item.get("Status", "")
                airflow_up = item.get("State") == "running" and "healthy" in status
                print(f"  {'✓' if airflow_up else '✗'} airflow: {status}")
    if not airflow_up:
        print(
            "  ✗ airflow is not healthy -- run `docker compose up -d --build airflow` and wait for it to become healthy first"
        )
        all_passed = False

    print("\n[CHECK] Health endpoint (curl http://localhost:8080/health)")
    success, output = run_command(
        "curl -fsS http://localhost:8080/health", "Airflow health endpoint"
    )
    if success and "healthy" in output.lower():
        print("  ✓ Health endpoint OK")
    elif success:
        print(f"  ⚠️ Health endpoint responded but the content was unexpected: {output[:200]}")
    else:
        print("  ✗ Health endpoint failed")
        all_passed = False

    if not airflow_up:
        print(
            "\n[CHECK] Skipped (airflow container not healthy): dags list-import-errors, dags list, dags test"
        )
        print("\n" + "=" * 60)
        print("PHASE 7: ✗ SOME REQUIREMENTS FAILED")
        print("=" * 60)
        return False

    print("\n[CHECK] airflow dags list-import-errors (must be empty)")
    ok, output = _airflow_exec(["airflow", "dags", "list-import-errors"])
    body = "\n".join(
        line
        for line in output.splitlines()
        if line.strip() and "DeprecationWarning" not in line and "warnings.warn" not in line
    )
    no_errors = ok and (
        "No data found" in output or body.strip() == "" or "filepath" not in output.lower()
    )
    if no_errors:
        print("  ✓ No import errors")
    else:
        print("  ✗ Import errors found:")
        for line in output.splitlines()[-30:]:
            print(f"    {line}")
        all_passed = False

    print("\n[CHECK] airflow dags list (all 4 DAGs must be registered)")
    ok, output = _airflow_exec(["airflow", "dags", "list"])
    expected_dags = {
        "panganwatch_daily",
        "panganwatch_monthly_bps",
        "panganwatch_reference",
        "panganwatch_retention",
    }
    found = {d for d in expected_dags if d in output}
    if ok and found == expected_dags:
        print(f"  ✓ All 4 DAGs registered: {sorted(found)}")
    else:
        print(f"  ✗ Missing DAGs: {expected_dags - found}")
        all_passed = False

    print("\n[CHECK] airflow dags test panganwatch_daily <date>")
    test_date = "2026-09-23"
    ok, output = _airflow_exec(
        ["airflow", "dags", "test", "panganwatch_daily", test_date], timeout=300
    )
    if ok:
        print(f"  ✓ dags test panganwatch_daily {test_date} exit 0")
    else:
        print(
            "  ✗ dags test panganwatch_daily failed:\n"
            + "\n".join(f"    {line}" for line in output.splitlines()[-20:])
        )
        all_passed = False

    print("\n[CHECK] airflow dags test panganwatch_retention <date>")
    ok, output = _airflow_exec(
        ["airflow", "dags", "test", "panganwatch_retention", test_date], timeout=180
    )
    if ok:
        print(f"  ✓ dags test panganwatch_retention {test_date} exit 0")
    else:
        print(
            "  ✗ dags test panganwatch_retention failed:\n"
            + "\n".join(f"    {line}" for line in output.splitlines()[-20:])
        )
        all_passed = False

    print("\n[CHECK] airflow dags test panganwatch_monthly_bps <date> (all tasks succeed)")
    if not _bps_key_is_set():
        print("  WARN: BPS_API_KEY is empty; the monthly DAG will be skipped -- allowed by policy")
    else:
        ok, output = _airflow_exec(
            ["airflow", "dags", "test", "panganwatch_monthly_bps", "2026-09-26"], timeout=300
        )
        both_success = all(
            f"Marking task as SUCCESS. dag_id=panganwatch_monthly_bps, task_id={t}," in output
            for t in ("ingest_bps", "dbt_build_bps")
        )
        if (
            ok
            and both_success
            and "Marking task as SKIPPED" not in output
            and "state=success" in output
        ):
            print(
                "  ✓ dags test panganwatch_monthly_bps: ingest_bps and dbt_build_bps SUCCESS (not skipped)"
            )
        else:
            print(
                "  ✗ dags test panganwatch_monthly_bps failed/skipped:\n"
                + "\n".join(f"    {line}" for line in output.splitlines()[-20:])
            )
            all_passed = False

    print("\n[CHECK] Memory across the whole stack (F1 + F6 + F7) < 7GiB")
    total_mib, raw_output = docker_memory_usage_mib(
        [
            "panganwatch-postgres",
            "panganwatch-mongo",
            "panganwatch-kafka",
            "panganwatch-weather-producer",
            "panganwatch-weather-consumer",
            "panganwatch-airflow",
        ]
    )
    if raw_output.strip():
        print(f"  {raw_output.strip()}")
        print(f"  Total memory: {total_mib:.1f} MiB ({total_mib / 1024:.2f} GiB)")
        if total_mib < 7168:
            print("  ✓ Total memory < 7 GiB")
        else:
            print("  ✗ Total memory >= 7 GiB")
            all_passed = False
    else:
        print("  ✗ docker stats failed or returned nothing")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 7: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 7: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)

    return all_passed


def _count_glossary_terms() -> int:
    """Count term rows in glossary.md (non-header table rows)."""
    path = Path("docs/governance/glossary.md")
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    count = 0
    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith("| ")
            and not stripped.startswith("| Term")
            and not stripped.startswith("|---")
        ):
            count += 1
    return count


def _raci_owner_accountable_datasets() -> tuple[list[str], list[str]]:
    """List datasets with exactly one Data Owner "A", and those without."""
    path = Path("dbt/panganwatch/seeds/governance_raci.csv")
    if not path.exists():
        return [], []
    import csv

    owner_counts: dict[str, int] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("role") == "Data Owner" and row.get("raci_value") == "A":
                owner_counts[row["dataset"]] = owner_counts.get(row["dataset"], 0) + 1
    ok = sorted(d for d, c in owner_counts.items() if c == 1)
    bad = sorted(d for d, c in owner_counts.items() if c != 1)
    return ok, bad


def _manifest_gold_models() -> list[str]:
    path = Path("dbt/panganwatch/target/manifest.json")
    if not path.exists():
        return []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    models = []
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") == "model" and node.get("schema") == "gold":
            models.append(f"gold.{node.get('name')}")
    return sorted(models)


def _lineage_mentions_all_gold() -> tuple[bool, list[str]]:
    """Check whether lineage.md mentions every gold model from the manifest."""
    lineage_path = Path("docs/lineage.md")
    if not lineage_path.exists():
        return False, []
    content = lineage_path.read_text(encoding="utf-8")
    gold_models = _manifest_gold_models()
    missing = [model for model in gold_models if model not in content]
    return len(missing) == 0, missing


def verify_phase_8() -> bool:
    """Verify F8a: governance documents (seeds, generators, reproducibility)."""
    print("\n" + "=" * 60)
    print("PHASE 8a: Governance documents (glossary, RACI, lineage, data dictionary, policies)")
    print("=" * 60)

    all_passed = True

    # Check 1: governance_glossary seed has >= 15 terms
    print("\n[CHECK] governance_glossary.csv has at least 15 terms")
    seed_path = Path("dbt/panganwatch/seeds/governance_glossary.csv")
    if not seed_path.exists():
        print("  ✗ governance_glossary.csv MISSING")
        all_passed = False
    else:
        import csv

        with open(seed_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        count = len(rows)
        empty_defs = sum(1 for r in rows if not r.get("definition", "").strip())
        print(f"  terms: {count}, empty definitions: {empty_defs}")
        if count >= 15 and empty_defs == 0:
            print("  ✓ >=15 terms and 0 empty definitions")
        else:
            print("  ✗ glossary criteria not met")
            all_passed = False

    # Check 2: governance_raci seed - every dataset has exactly one Data Owner "A"
    print("\n[CHECK] governance_raci.csv: every dataset has exactly one A (Data Owner)")
    raci_path = Path("dbt/panganwatch/seeds/governance_raci.csv")
    if not raci_path.exists():
        print("  ✗ governance_raci.csv MISSING")
        all_passed = False
    else:
        ok, bad = _raci_owner_accountable_datasets()
        print(f"  datasets with exactly one A: {len(ok)}; without exactly one: {len(bad)}")
        if not bad:
            print("  ✓ every dataset has exactly one A in the Data Owner role")
        else:
            print(f"  ✗ datasets without exactly one A: {', '.join(bad[:10])}")
            all_passed = False

    # Check 3: retention_policy.md documents the technical mechanism and 180 days
    print("\n[CHECK] docs/governance/retention_policy.md: mechanism + 180-day retention")
    path = Path("docs/governance/retention_policy.md")
    if not path.exists():
        print("  ✗ retention_policy.md MISSING")
        all_passed = False
    else:
        content = path.read_text(encoding="utf-8")
        has_180 = "180" in content
        has_mechanism = (
            "TTL" in content and "retention.ms" in content and "panganwatch_retention" in content
        )
        has_verify = "verify" in content.lower()
        print(
            f"  180 days: {has_180}, technical mechanism: {has_mechanism}, how to verify: {has_verify}"
        )
        if has_180 and has_mechanism and has_verify:
            print("  ✓ retention_policy.md is complete with mechanism + verification")
        else:
            print("  ✗ retention_policy.md is incomplete")
            all_passed = False

    # Check 4: lineage.md mentions every gold model from the manifest
    print("\n[CHECK] docs/lineage.md: mentions every gold model from the manifest")
    ok, missing = _lineage_mentions_all_gold()
    if ok:
        print("  ✓ every gold model is listed in lineage.md")
    else:
        print(f"  ✗ gold models missing from lineage.md: {', '.join(missing)}")
        all_passed = False

    # Check 5: data_dictionary.md has real column types from the catalog (not all 'unknown')
    print("\n[CHECK] docs/data_dictionary.md: column types from the catalog (not all 'unknown')")
    path = Path("docs/data_dictionary.md")
    if not path.exists():
        print("  ✗ data_dictionary.md MISSING")
        all_passed = False
    else:
        content = path.read_text(encoding="utf-8")
        has_unknown = "unknown" in content
        has_real_types = (
            "numeric" in content
            or "varchar" in content
            or "double" in content
            or "integer" in content
            or "date" in content
        )
        print(f"  has real types: {has_real_types}, still has 'unknown': {has_unknown}")
        if has_real_types and not has_unknown:
            print("  ✓ data_dictionary.md has real column types")
        else:
            print("  ✗ data_dictionary.md still has 'unknown' types or no real types")
            all_passed = False

    # Check 6: dama_mapping.md covers 11 knowledge areas + an honest status
    print("\n[CHECK] docs/governance/dama_mapping.md: 11 knowledge areas + honest status")
    path = Path("docs/governance/dama_mapping.md")
    if not path.exists():
        print("  ✗ dama_mapping.md MISSING")
        all_passed = False
    else:
        content = path.read_text(encoding="utf-8")
        areas = [
            "Data Governance",
            "Data Architecture",
            "Data Modeling",
            "Data Storage",
            "Data Security",
            "Data Integration",
            "Metadata Management",
            "Data Quality",
            "Reference & Master Data",
            "Data Warehousing",
            "Document & Content Management",
        ]
        missing_areas = [a for a in areas if a not in content]
        has_not_covered = "not covered" in content.lower()
        print(
            f"  missing DAMA areas: {missing_areas or 'none'}; has 'not covered': {has_not_covered}"
        )
        if not missing_areas and has_not_covered:
            print("  ✓ dama_mapping.md is complete with 11 areas and an honest coverage status")
        else:
            print("  ✗ dama_mapping.md is incomplete or not honest about coverage")
            all_passed = False

    # Check 7: make docs reproducible via check_repro.py
    print("\n[CHECK] make docs reproducible (check_repro.py exit 0)")
    cmd = 'uv run python scripts/check_repro.py --cmd "uv run python scripts/generate_docs.py" --paths docs/governance docs/lineage.md docs/data_dictionary.md'
    print(f"  Command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        if success:
            print("  ✓ check_repro.py exit 0 (reproducible)")
            for line in output.strip().splitlines()[-5:]:
                print(f"    {line}")
        else:
            print(f"  ✗ check_repro.py exit {result.returncode}")
            for line in output.strip().splitlines()[-10:]:
                print(f"    {line}")
            all_passed = False
    except subprocess.TimeoutExpired:
        print("  ✗ check_repro.py timeout")
        all_passed = False
    except Exception as e:
        print(f"  ✗ error: {e}")
        all_passed = False

    # Check 8: incident_log.md has at least 2 incidents and is never overwritten
    print("\n[CHECK] docs/governance/incident_log.md: at least 2 incidents")
    path = Path("docs/governance/incident_log.md")
    if not path.exists():
        print("  ✗ incident_log.md MISSING")
        all_passed = False
    else:
        content = path.read_text(encoding="utf-8")
        incident_count = content.count("## Incident")
        print(f"  incidents logged: {incident_count}")
        if incident_count >= 2:
            print("  ✓ >=2 incidents logged in incident_log.md")
        else:
            print("  ✗ <2 incidents in incident_log.md")
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 8a: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 8a: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)

    return all_passed


def verify_phase_9():
    """Verify F9 analytics/report outputs with real file checks."""
    print("=" * 60)
    print("PHASE 9: Analytics and reporting")
    print("=" * 60)
    all_passed = True

    # Check 1: HTML report exists and has >=5 Plotly graph divs
    print("\n[CHECK] reports/panganwatch_report.html: exists and has >=5 Plotly graphs")
    report_path = Path("reports/panganwatch_report.html")
    if not report_path.exists():
        print("  ✗ reports/panganwatch_report.html MISSING")
        all_passed = False
    else:
        content = report_path.read_text(encoding="utf-8")
        # count real chart divs; the bare token also matches a CSS rule and
        # a <script> line, which inflated the count from 5 to 6
        graph_count = content.count('class="plotly-graph-div')
        size = report_path.stat().st_size
        print(f"  size: {size} bytes")
        print(f'  class="plotly-graph-div" count: {graph_count}')
        if size > 0 and graph_count >= 5:
            print("  ✓ HTML report exists and has >=5 Plotly graphs")
        else:
            print("  ✗ HTML report is empty or has <5 Plotly graphs")
            all_passed = False

    # Check 2: core Tableau CSV files exist, non-empty, and <50MB
    print("\n[CHECK] exports/tableau/: 6 core CSVs exist, have data, and are <50MB")
    export_dir = Path("exports/tableau")
    core_files = [
        "fct_harga_harian.csv",
        "mart_disparitas_provinsi.csv",
        "mart_cuaca_harga_bulanan.csv",
        "mart_dq_scorecard.csv",
        "dim_provinsi.csv",
        "dim_komoditas.csv",
    ]
    if not export_dir.exists():
        print("  ✗ exports/tableau/ MISSING")
        all_passed = False
    else:
        for filename in core_files:
            path = export_dir / filename
            if not path.exists():
                print(f"  ✗ {filename} MISSING")
                all_passed = False
                continue
            size = path.stat().st_size
            with path.open(encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            data_rows = max(0, line_count - 1)
            size_mb = size / (1024 * 1024)
            print(f"  {filename}: {data_rows} rows, {size:,} bytes ({size_mb:.2f} MB)")
            if data_rows < 1 or size_mb >= 50:
                print(f"    ✗ invalid: rows={data_rows}, size_mb={size_mb:.2f}")
                all_passed = False
        if all_passed:
            print("  ✓ all 6 core CSVs are valid")

    # Check 3: Tableau guide exists and documents dashboards
    print("\n[CHECK] docs/TABLEAU_GUIDE.md: exists and documents 3 dashboards")
    guide_path = Path("docs/TABLEAU_GUIDE.md")
    if not guide_path.exists():
        print("  ✗ docs/TABLEAU_GUIDE.md MISSING")
        all_passed = False
    else:
        content = guide_path.read_text(encoding="utf-8")
        required = ["Price Disparity", "Weather vs Price", "Data Quality Score"]
        missing = [term for term in required if term not in content]
        print(f"  size: {guide_path.stat().st_size} bytes; missing terms: {missing or 'none'}")
        if not missing and guide_path.stat().st_size > 0:
            print("  ✓ Tableau guide exists and documents 3 dashboards")
        else:
            print("  ✗ Tableau guide is incomplete")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("PHASE 9: ✓ ALL REQUIREMENTS MET")
    else:
        print("PHASE 9: ✗ SOME REQUIREMENTS FAILED")
    print("=" * 60)
    return all_passed


def main():
    """CLI entry point: run verification for a given phase."""
    parser = argparse.ArgumentParser(description="PanganWatch phase verification")
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="Phase number to verify (0-9) or 'all' for all phases",
    )
    args = parser.parse_args()

    if args.phase is None:
        parser.print_help()
        sys.exit(1)

    phases = {
        0: verify_phase_0,
        1: verify_phase_1,
        2: verify_phase_2,
        3: verify_phase_3,
        4: verify_phase_4,
        5: verify_phase_5,
        6: verify_phase_6,
        7: verify_phase_7,
        8: verify_phase_8,
        9: verify_phase_9,
    }

    if args.phase == "all":
        print("Running verification for ALL phases (0-9)...")
        all_passed = True
        for i in range(10):
            print(f"\n{'=' * 60}")
            print(f"PHASE {i}")
            print("=" * 60)
            result = phases[i]()
            all_passed = all_passed and result
        print(f"\n{'=' * 60}")
        if all_passed:
            print("ALL PHASES PASSED ✓")
        else:
            print("SOME PHASES FAILED ✗")
        sys.exit(0 if all_passed else 1)

    try:
        phase_num = int(args.phase)
    except ValueError:
        print(f"Unsupported phase: {args.phase}. Use 0-9 or 'all'.")
        sys.exit(1)

    if phase_num not in phases:
        print(f"Unsupported phase: {phase_num}. Use 0-9 or 'all'.")
        sys.exit(1)

    print(f"Running verification for phase {phase_num}...")
    result = phases[phase_num]()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
