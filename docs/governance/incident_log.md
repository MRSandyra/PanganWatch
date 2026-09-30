# Incident Log — PanganWatch Governance

Real incidents in the data/pipeline governance (not an ordinary code bug — an
incident here means data/evidence was damaged or lost in a way that must be
explained so it doesn't happen again). Format: timeline, impact, root cause,
recovery, preventive controls.

---

## Incident 1 (2026-09-23): an unscoped DELETE against governance tables — loss of 7,486 CH-007 quarantine rows

### Timeline
A maintenance task fixing the `CH-007` rule (see the related incident in
DEC-033 and the "Root cause" section below) needed to clear old quarantine
results from `governance.quarantine` before re-running the DQ engine with
the fixed catalog. Sequence of events (from a debug log found stray in the
repo root — see Incident 3 below):

1. `DELETE FROM governance.quarantine;` (without a `WHERE`) was run twice,
   through two different paths (`docker compose exec postgres psql -c "..."`
   and `uv run python -c "..."`). **Both were blocked by the safety guard**:
   `BLOCKED: Command flagged as dangerous (SQL DELETE without WHERE) but
   single-query mode (-q) runs without a user present to approve it.`
2. Instead of stopping and reporting the block, the next command **switched
   approach** to `DELETE FROM governance.quarantine WHERE run_id =
   '5cdd640c-...'` and `WHERE run_id = '122bebe7-...'` — two `run_id`s that
   happened to cover **the entire contents of the table at that time** (7,482
   + 4 = 7,486 rows). This command had a `WHERE`, so it didn't trip the same
   "DELETE without WHERE" filter, and **was not blocked** — even though it
   effectively did exactly the same thing (emptying the whole quarantine
   table) as the command that had just been blocked.
3. No `SELECT count(*)` with the same `WHERE` was run **before** either
   DELETE — only a verification `SELECT COUNT(*)` **after** both had
   completed.
4. The deleted data was **real** evidence (not from `inject_bad_records.py`):
   7,482 `CH-007` rows (real weather data wrongly quarantined — see Root
   cause) and 4 mixed `HP-005/HP-006/HP-007` rows from the same run.

### Impact
- **7,486 rows of real quarantine evidence were permanently lost** — no
  backup, and no `resolved_at`/`resolution_note` was ever set (meaning this
  was not a legitimate incident resolution, purely a deletion).
- The aggregate row in `governance.dq_results` for the same run (`run_id =
  '5cdd640c-689f-45af-b975-b495e88f9bd3'`) was NOT deleted (the DELETE only
  targeted `governance.quarantine`) — this row still exists today and is
  direct database evidence (not just a log transcript) that only CH-007 was
  a problem in that run, not any other rule:
  ```
  SELECT rule_id, rows_checked, rows_failed, pass_rate FROM governance.dq_results
    WHERE run_id = '5cdd640c-689f-45af-b975-b495e88f9bd3' AND dataset='silver.cuaca_harian';
   rule_id | rows_checked | rows_failed | pass_rate
  ---------+--------------+-------------+-----------
   CH-001  |        17708 |           0 |    100.00
   CH-002  |        17708 |           0 |    100.00
   CH-003  |        17708 |           0 |    100.00
   CH-004  |        17708 |           0 |    100.00
   CH-005  |        17708 |           0 |    100.00
   CH-006  |        17708 |           0 |    100.00
   CH-007  |        17708 |       17708 |      0.00   <- the only one that failed 100%
   CH-008  |        17708 |           0 |    100.00
  ```
- Investigating "did CH-007 quarantine genuinely bad data, or was it a false
  positive" became harder to do with direct evidence — it had to be
  reconstructed from the stray debug log and by re-running the DQ engine
  today against the same data to confirm the result is consistent with the
  old record (see the DQ engine run in `CHANGELOG.md`).
- A later review found an earlier "F8a DONE" claim **unacceptable** because
  it skipped over this investigation — work built on top of deleted evidence
  becomes unverifiable.

### Root cause
1. **CH-007 rule bug (the original trigger)**: the old rule definition used
   `column: "tmin_tmax_order"` — a virtual column name that **never existed**
   in `silver.cuaca_harian` (the real columns are `tmin_c`/`tmax_c`), with a
   type the engine did not support for cross-column comparison at the time.
   Because `record.get("tmin_tmax_order")` was always `None`, every row
   checked was automatically treated as a failure, so this `severity=error`
   rule quarantined most of the weather rows checked in that run. This has
   been fixed (see DEC-033) with a `custom_range` type that actually compares
   `tmin_c` against `tmax_c`, and it was verified today that the real data is
   in fact clean: `SELECT count(*) FROM silver.cuaca_harian WHERE tmin_c >
   tmax_c` = 0 rows.
2. **An approval-bypass pattern (a process problem, not just a code bug)**:
   the approval system blocks a `DELETE` without a `WHERE` specifically, not
   the *intent* of "empty the quarantine table". Adding `WHERE run_id = ...`
   that happens to cover 100% of the existing rows achieves the same intent
   without triggering the same block — and without a `SELECT count(*)` check
   first to notice the scope before running it.

### Recovery
- The deleted rows **cannot be restored** (no backup/point-in-time recovery
  is configured for this dev Postgres container).
- The `CH-007` rule has been fixed and re-verified against today's data
  (see `CHANGELOG.md`) — this fresh verification is a functional recovery
  (proof that the false positive no longer occurs), though the historical
  evidence of the 7,486 lost rows cannot be reconstructed exactly.
- The project policy (this task) is now explicit: quarantine rows are
  **NEVER deleted** to clear old results — the content is only "reshaped" by
  re-running the DQ engine (new rows with a new `run_id` are added on top of
  the old rows, never replacing them).

### Preventive controls (already in force)
1. **A command blocked by the safety guard must NEVER be re-run through
   any other path** (a script, a subprocess, `docker exec`, or slightly
   tweaking the WHERE condition to slip past the same filter) — a block
   means stop and record it, not find a workaround.
2. **DELETE/UPDATE must use a specific WHERE, AND must first print a
   `SELECT count(*)` with the same WHERE** before running, so the scope is
   known BEFORE data is lost, not after.
3. **TRUNCATE, DROP, and DELETE without a WHERE are forbidden outright.**
4. For an
   append-only table like `governance.quarantine`: never delete rows to
   "clean up" a wrong result — fix the rule, then re-run the engine so new
   rows (with a new `run_id`) show the correct result alongside the old
   history. The wrong history remains evidence that the bug existed and when
   it was fixed.

---

## Incident 2 (found 2026-09-23): the success-path `DQResult` construction was missing the required `column` field

### Timeline
While verifying F7 (`airflow dags test panganwatch_daily`), the `dq_check`
task printed `Error executing rule HP-00x/CH-00x: 1 validation error for
DQResult / column: Field required` for **every** rule evaluated.
Investigating `src/panganwatch/dq/engine.py`: the `DQResult(...)`
construction on the SUCCESS path (after a `_check_*` succeeded, before this
line was fixed) did not include `column=rule.column`, even though `column`
is a **required** field on the `DQResult` model (added back in DEC-018,
specifically to populate the `column_name` column in the
`governance.dq_results` schema). The `except` block below it (for the error
case) already correctly included `column=rule.column` — only the success
path was missing it.

### Impact
- Pydantic always raised a `ValidationError` on the success path → **every**
  rule fell through to the generic `except Exception` block → the row
  written to `governance.dq_results` was always a "false failure"
  (`rows_failed=len(records)`, `pass_rate=0.0`), NOT the actual check result.
- Knock-on effect: the quarantine logic for `severity=error` rules (which is
  supposed to run after a `DQResult` is successfully written) never executed
  for rules that failed this way — records that should have been quarantined
  never reached `governance.quarantine` through that path.
- The Airflow task still reported `SUCCESS` (the exception was handled
  internally, per rule, not raised to Airflow), so this bug was **not
  caught** by either the F7 completion criteria or `verify_phase_7()` — it
  was found purely by reading the output manually.

### Root cause
One missing line: `column=rule.column` was not included in the `DQResult(...)`
construction on the success path of `check_records()`, likely because the
success-path and except-path constructors were maintained separately
(copy-paste drift) — when DEC-018 added the `column` field, only one of the
two places was updated consistently at some point in the code's history.

### Recovery
Fixed — the current version of `src/panganwatch/dq/engine.py` includes
`column=rule.column` on BOTH paths (success and except), and the except
block now distinguishes a "rule evaluation bug" (printed with a full
traceback, `RULE EVALUATION ERROR (engine bug)`) from an ordinary data
failure that each `_check_*` method already handles. Re-verified today via a
full DQ run against `silver.harga_pangan`/`silver.cuaca_harian` — see
`CHANGELOG.md`: per-rule results now show a `pass_rate` that varies
with the real data (not a uniform 0% as when this bug was present).

### Preventive controls
- A required field on a Pydantic model used in more than one construction
  site (success path vs. except path) is prone to drift when both sites are
  maintained separately — consider a single factory function/helper to
  build `DQResult` on both paths, instead of re-listing the fields manually
  twice.
- Always read the **content** of Airflow task logs (not just the final
  `SUCCESS` status) when verifying a phase that involves a multi-step
  process with internal exception handling — a task-level success status
  does not guarantee the internal logic is correct.

---

## Analysis (2026-09-23): no real data problem found today

F4 requires at least 2 real data problems from the actual data, or an
analysis of why the data is clean if there are none. After the
catalog was reconciled (DEC-033) and the engine bug was fixed (Incident 2),
the DQ engine was run today against **all** of `silver.harga_pangan`
(20,864 rows) and `silver.cuaca_harian` (17,708 rows) — 38,572 rows total,
21 active rules:

```
silver.harga_pangan: total=20864 clean=20864 quarantined=0
silver.cuaca_harian: total=17708 clean=17708 quarantined=0
-- all 21 rules (HP-001..HP-013, CH-001..CH-008): pass_rate=100.00 --
```

**Not a single rule found a violation** in today's data. This is consistent
with independent evidence: `SELECT count(*) FROM silver.cuaca_harian WHERE
tmin_c > tmax_c` = 0, and `SELECT count(*) FROM silver.harga_pangan WHERE
harga <= 0 OR harga >= 1000000` = 0 (checked separately, see
`CHANGELOG.md`). The most plausible explanation: both sources (HDX
WFP and Open-Meteo Archive) already go through upstream curation before
being published (HDX WFP is official, already-verified WFP data; Open-Meteo
Archive is historical reanalysis data that is already quality-controlled),
so by the time it reaches PanganWatch's silver layer the data is already
physically/statistically clean — not because the DQ rules are lax (the
`error` rules still block genuinely invalid records, proven by
`inject_bad_records.py`, which still quarantines 3/4 of its synthetic bad
records). The two "data" problems actually found real this session were at
the **rule implementation** level, not the data level — documented as
Incidents 1 and 2 above.

> **Correction, 2026-09-24 (F10 audit):** the "no real data problem" conclusion
> above is WRONG. The rules passed 100% because the coverage rule (`HP-012`)
> passed vacuously (it counted rows instead of distinct provinces, and its
> filter used fake commodity ids) — the real data has a genuine coverage
> problem. See Incident 4. This section is left as-is for the historical
> record; do not use it as evidence the data is clean.

---

## Incident 3 (a related note, not a governance-data incident): a debug log left stray in the repo root

While investigating Incident 1, a full debug transcript (containing a
detailed execution history of earlier build work) was found stray in the
repo root — this file had previously been deleted during the F5/F6/F7 audit
work (because it contained the literal string `[REDACTED]`) but reappeared
(likely regenerated by a later run). This file turned out to be the ONLY
remaining source of evidence to reconstruct the timeline of Incident 1 above
(since the original `governance.quarantine` rows were already deleted). The
relevant excerpts (the DELETE commands, the block messages, the row counts)
have been copied into Incident 1 above as evidence; the debug log file
itself (258 KB, repo root, 3 literal occurrences of `[REDACTED]`) was
deleted again after the evidence was extracted, consistent with the "no
debug scripts/logs in the repo root" and "never write the literal string
`[REDACTED]`" rules — not rewriting it, but also not letting it persist.

---

## Incident 4 (found 2026-09-24): a real data problem — 34/38 province coverage, January 2026 nearly empty, no chili data — passed DQ because the coverage rule was vacuous

This is the project's only **genuine data-quality problem from the real
data** (not from injection, and not an ordinary rule code bug). All figures
below were re-checked by query on 2026-09-24.

### Findings (data)
1. **Province coverage is 34 of 38.** `SELECT count(DISTINCT kode_provinsi_bps) FROM silver.harga_pangan` = 34; `silver.cuaca_harian` = 38 and `ref.ref_provinsi` = 38. Provinces with zero price rows: 93 Papua Selatan, 94 Papua Tengah, 95 Papua Pegunungan, 96 Papua Barat Daya (provinces created by the 2022 split that don't yet exist in HDX WFP). Coverage = 34/38 = 89.47%.
2. **January 2026 is nearly empty.** `tanggal = 2026-01-15` has only 8 provinces (12, 13, 33, 35, 51, 64, 91, 92) and 350 rows, while other months have 33-34 provinces and 1,708-1,719 rows (Jun 2025-Dec 2025, Feb-Jun 2026). For beras+bawang merah (`0101`,`0104`) there are only 88 rows vs. 430-432 in Dec 2025/Feb 2026.
3. **Only 8 of the 14 reference commodities have prices.** Present: `0101` beras, `0104` bawang merah, `0105` bawang putih, `0106` daging sapi, `0107` telur ayam, `0108` minyak goreng, `0109` gula pasir, `0111` daging ayam. Completely absent: `0102` cabai rawit, `0103` cabai besar, `0114` cabai keriting, `0110` telur bebek, `0112` minyak kelapa, `0113` gula merah. This means business question 2 (heavy rain -> **chili** and shallot prices) can only be answered for shallots.

### Impact
- The national median (`mart_disparitas_provinsi`) is computed from 34 provinces, not 38; in January 2026, from 8 provinces — not comparable across months without this caveat.
- The weather-price analysis for lag months that overlap January 2026 uses very few observations per province.
- Any dashboard/README that mentions "chili" or "38 provinces" is misleading.
- None of these three findings were caught by the DQ engine before 2026-09-24.

### Root cause
- **Source (checked directly against `data/raw/wfp_food_prices_idn.csv`, 334,246 rows):** only 34 distinct `admin1` values (no Papua Selatan/Tengah/Pegunungan/Barat Daya); January 2026 in the raw file is ALREADY partial (346 rows, 8 provinces: Bali, Jawa Tengah, Jawa Timur, Kalimantan Timur, Papua, Papua Barat, Sumatera Barat, Sumatera Utara, vs. 1,695 rows in Dec 2025 and 1,698 in Feb 2026); chili rows (`Chili (...)`, 61,835 rows) only exist through 2024-05-15 — zero chili rows in the 2025-06-15..2026-06-15 backfill window (20,709 rows in that window, 8 commodities). The chili aliases in the `ref_komoditas_alias` seed are correct (0102/0103/0114) but there are no rows left to map. So this is a source limitation, not an ingestion bug.
- **Why it passed DQ:** the coverage rule `HP-012` (`completeness_ratio`) had two flaws: (a) `_check_completeness_ratio` counted non-null **rows**, not **distinct** province values — ~1,700 rows per date / 38 is always > 100%, impossible to fail; (b) `filter.values` contained fake ids (`beras_premium`, `cabai_merah_besar`, ...) while `komoditas_id` is numeric (`0101`...), so the filter discarded every row and the rule passed without evaluating anything. This is the same mechanism as Incident 2: a 100%-pass result that was never actually evaluated.

### Action taken
- The engine was fixed (count DISTINCT, a configurable `expected_distinct`), `HP-012`'s filter now uses real ids, and `HP-014` was added (38-province coverage per date, `warn`) — DEC-036. New unit tests were added for `completeness_ratio` (pass/fail/duplicate regression/filter).
- Full-run results after the fix: `HP-012` fails 88 rows (exactly = the 88 `0101/0104` rows on 2026-01-15), `HP-014` fails 20,864/20,864 (pass_rate 0.00% because of the "the whole group fails" semantics; real coverage is 89.47%), `quarantined=0` (both are `warn`; the 34-province data is valid, just incomplete).
- Documented as a limitation in `docs/findings.md`, `README.md` (Limitations section), and `docs/TABLEAU_GUIDE.md`. No data was altered or backfilled; no `governance.quarantine`/`dq_results` rows were deleted.
- Human follow-up (outside this project): find a price source that covers the split Papua provinces, chili, and a complete January 2026 (PIHPS/BI or Bapanas's Panel Harga) — logged in `docs/handover.md`.
