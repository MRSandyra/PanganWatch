# Final verification

**Migration status: CLOUD_PARTIAL.**

The Databricks Free Edition implementation has been executed successfully with
actual cloud artifacts and a published dashboard.  It is deliberately not
labelled `CLOUD_VERIFIED` or `PORTFOLIO_READY`: a parity comparison with the
pre-migration local/legacy database has not been executed.  The reconciliation
below is a source-replay check against the uploaded immutable snapshots and
cloud Bronze/Silver transformations; it is not a legacy parity assertion.

## Verified in Databricks

| Area | Observed result | Status |
|---|---|---|
| Workspace preflight | Unity Catalog `workspace`, required schemas, and `/Volumes/workspace/pw_landing/snapshots` were available | PASSED |
| Reference dimensions | 38 provinces, 14 commodities, 34 province aliases, and 69 commodity aliases loaded | PASSED |
| Price Bronze/Silver | `workspace.pw_bronze.hdx_wfp_raw` and `workspace.pw_silver.harga_pangan` built | PASSED |
| Weather Bronze/Silver | `workspace.pw_bronze.open_meteo_raw` and `workspace.pw_silver.cuaca_harian` built; 269,496 daily rows across 38 provinces, 2007-01-15 through 2026-06-15 | PASSED |
| DQ governance | 14 price and 8 weather rules evaluated; no blocking rules; four non-blocking price warnings remain | PASSED |
| Gold marts | `fct_harga_bulanan`, `mart_disparitas_provinsi`, and `mart_cuaca_harga_bulanan` built | PASSED |
| Source replay | Price 164,750 expected/actual and weather 269,496 expected/actual; zero missing or unexpected rows | PASSED |
| Databricks job | `panganwatch_batch` completed successfully: nine tasks green, 49 queries, 5,077,195 rows read, 434,401 rows written | PASSED |
| Published dashboard | Four published pages cover national commodity prices, DQ, provincial disparity, and monthly rainfall | PASSED |

Sanitized evidence is recorded in [cloud-run-20261111.md](evidence/cloud-run-20261111.md).

## Known limitations and decisions

- **Legacy parity is NOT_EXECUTED.** The prior local system has not been
  compared row-for-row against the cloud result. This is the reason for the
  `CLOUD_PARTIAL` status.
- WFP national aggregate prices cover 2007-01 through 2020-03 (1,263 rows,
  158 months). Provincial price coverage is 2016-07 through 2026-06 (27,635
  rows, 85 months). The two series must not be presented as a continuous,
  directly comparable national-to-provincial time series outside their overlap.
- 390 price records remain in governance as unmapped. The source commodity
  labels are `Fuel (kerosene)`, `Milk (condensed)`, and `Wheat flour`; they are
  retained for review rather than forced into a reference commodity.
- Non-blocking price warnings `HP-010`, `HP-011`, `HP-012`, and `HP-014` remain
  visible in the dashboard. Error-severity DQ rules passed.
- The price/weather chart is descriptive only. It does not establish that
  rainfall causes food-price changes.
