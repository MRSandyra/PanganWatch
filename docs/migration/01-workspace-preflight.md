# Workspace preflight

**Status:** NOT_EXECUTED — no authenticated Databricks workspace URL or OAuth session is available in this environment. No cloud object was created.

Before deployment, the owner must run `databricks auth login --host <actual-free-edition-workspace-url>` and, without printing credentials, record the following in `evidence/preflight.json`: identity, Free Edition status, usable catalog, schema/managed-table/volume create permissions, serverless notebook compute, SQL warehouse, Lakeflow Jobs, AI/BI Dashboard, API/CLI support, and quotas.

Run `databricks/notebooks/00_preflight.py` after setting `PANGANWATCH_CATALOG` to the verified catalog. It creates only `pw_*` schemas and `pw_landing.snapshots`. If any creation fails, retain the sanitized error and use an authorized project-prefixed namespace; do not assume `main`, use a paid plan, or create external cloud storage.
