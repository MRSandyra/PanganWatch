"""Check DAG files in the dags directory.

This script validates that all required DAG files exist and can be imported.
"""

from pathlib import Path

from airflow.models import DagBag


def main():
    print("Checking DAG files in dags/ directory...")

    # Check for expected DAG files
    expected_dags = [
        "panganwatch_daily.py",
        "panganwatch_monthly_bps.py",
        "panganwatch_reference.py",
        "panganwatch_retention.py",
    ]

    dags_dir = Path("dags")
    missing_dags = []

    for dag_file in expected_dags:
        dag_path = dags_dir / dag_file
        if dag_path.exists():
            print(f"✓ Found {dag_file}")
        else:
            print(f"✗ Missing {dag_file}")
            missing_dags.append(dag_file)

    # Try to load DAGs
    print("\nLoading DAGs...")
    dagbag = DagBag(dags_folder=str(dags_dir), include_examples=False)

    if dagbag.import_errors:
        print(f"✗ DAG import errors ({len(dagbag.import_errors)}):")
        for dag_id, error in dagbag.import_errors.items():
            print(f"  {dag_id}: {error}")
    else:
        print(f"✓ Successfully loaded {len(dagbag.dags)} DAGs:")
        for dag_id in sorted(dagbag.dags.keys()):
            print(f"  {dag_id}")

    # Summary
    if not missing_dags and not dagbag.import_errors:
        print("\n✓ All checks passed!")
        return 0
    else:
        print("\n✗ Some checks failed!")
        return 1


if __name__ == "__main__":
    exit(main())
