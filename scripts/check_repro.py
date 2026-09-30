"""Reproducibility checker without git.

Computes SHA-256 hash of all files in specified paths, runs a command,
then recomputes hashes. Exits 0 if no changes, 1 if files changed.
"""

import argparse
import hashlib
import sys
from pathlib import Path


def compute_hashes(paths: list[str]) -> dict[str, str]:
    """Compute SHA-256 hash for all files in given paths."""
    hashes = {}

    for path_str in paths:
        path = Path(path_str)

        if not path.exists():
            continue

        if path.is_file():
            hashes[str(path)] = hash_file(path)
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    hashes[str(file_path)] = hash_file(file_path)

    return hashes


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return "ERROR_READING_FILE"


def main():
    parser = argparse.ArgumentParser(description="Check reproducibility without git")
    parser.add_argument("--cmd", required=True, help="Command to run")
    parser.add_argument("--paths", required=True, nargs="+", help="Paths to check")

    args = parser.parse_args()

    # Compute hashes before
    print(f"Computing hashes for: {args.paths}")
    hashes_before = compute_hashes(args.paths)
    files_before = set(hashes_before.keys())

    # Run command
    import subprocess

    print(f"\nRunning: {args.cmd}")
    result = subprocess.run(args.cmd, shell=True)

    if result.returncode != 0:
        print(f"\nCommand failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(2)

    # Compute hashes after
    print("\nRecomputing hashes...")
    hashes_after = compute_hashes(args.paths)
    files_after = set(hashes_after.keys())

    # Check for changes
    added = files_after - files_before
    removed = files_before - files_after
    modified = {f for f in files_before & files_after if hashes_before[f] != hashes_after[f]}

    if not (added or removed or modified):
        print("\n✓ No changes detected - reproducible")
        sys.exit(0)

    # Report changes
    print("\n✗ Changes detected:", file=sys.stderr)

    if added:
        print(f"\nAdded ({len(added)} files):", file=sys.stderr)
        for f in sorted(added)[:10]:
            print(f"  + {f}", file=sys.stderr)
        if len(added) > 10:
            print(f"  ... and {len(added) - 10} more", file=sys.stderr)

    if removed:
        print(f"\nRemoved ({len(removed)} files):", file=sys.stderr)
        for f in sorted(removed)[:10]:
            print(f"  - {f}", file=sys.stderr)
        if len(removed) > 10:
            print(f"  ... and {len(removed) - 10} more", file=sys.stderr)

    if modified:
        print(f"\nModified ({len(modified)} files):", file=sys.stderr)
        for f in sorted(modified)[:10]:
            print(f"  M {f}", file=sys.stderr)
        if len(modified) > 10:
            print(f"  ... and {len(modified) - 10} more", file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
