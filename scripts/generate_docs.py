"""Generate all governance documentation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panganwatch.governance import (
    data_dictionary_main,
    glossary_main,
    lineage_main,
    policies_main,
    raci_main,
)


def main():
    print("Generating governance documentation...")
    print("=" * 50)

    print("\n1/5 Generating glossary.md...")
    glossary_main()

    print("\n2/5 Generating raci.md...")
    raci_main()

    print("\n3/5 Generating retention and DAMA mapping docs...")
    policies_main()

    print("\n4/5 Generating lineage.md...")
    lineage_main()

    print("\n5/5 Generating data_dictionary.md...")
    data_dictionary_main()

    print("\n" + "=" * 50)
    print("All governance documentation generated successfully!")
    print("Output files:")
    print("  - docs/governance/glossary.md")
    print("  - docs/governance/raci.md")
    print("  - docs/lineage.md")
    print("  - docs/data_dictionary.md")
    print("  - docs/governance/retention_policy.md (static)")
    print("  - docs/governance/dama_mapping.md (static)")


if __name__ == "__main__":
    main()
