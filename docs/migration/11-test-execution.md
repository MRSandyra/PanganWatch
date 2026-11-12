# Test execution report

| Check | Result | Evidence |
|---|---|---|
| Python syntax | PASSED | `python -m compileall -q databricks scripts/...` exited 0 on 2026-11-09 |
| Migration Ruff lint / format | PASSED | `ruff check` and `ruff format --check` passed before the local virtualenv recreation attempt |
| `pytest databricks/tests` | PASSED | `uv run pytest -q databricks/tests` completed with 25 tests passed after dependencies became available |
| Existing project tests | NOT_EXECUTED | same missing dependency environment; legacy source was not altered |
| Databricks integration | PASSED | Actual Free Edition execution recorded in `evidence/cloud-run-20261111.md`: Bronze/Silver/DQ/Gold/source replay/job/dashboard |

The earlier `.venv` incident is retained as historical context. The current
Databricks migration tests have since passed; local legacy tests remain outside
the migration verification scope.
