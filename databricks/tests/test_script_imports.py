import runpy
import sys
from pathlib import Path


def test_migration_scripts_add_the_repository_root_before_importing_modules():
    project_root = Path(__file__).resolve().parents[2]
    scripts = [
        "export_frozen_snapshot.py",
        "generate_snapshot_manifest.py",
        "prepare_databricks_upload.py",
        "compare_local_cloud.py",
        "fetch_open_meteo_snapshot.py",
    ]
    for script in scripts:
        script_path = project_root / "scripts" / script
        namespace = runpy.run_path(str(script_path), run_name=f"test_{script.replace('.', '_')}")
        assert namespace["PROJECT_ROOT"] == project_root
        assert str(project_root) in sys.path
