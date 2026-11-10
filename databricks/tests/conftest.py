"""Make local tests mirror the Databricks notebook import root.

The Databricks runtime already owns the top-level ``databricks`` package, so
project modules are intentionally imported as ``src`` after adding the
repository's ``databricks`` directory to ``sys.path``.
"""

import sys
from pathlib import Path


DATABRICKS_DIRECTORY = Path(__file__).resolve().parents[1]
if str(DATABRICKS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(DATABRICKS_DIRECTORY))
