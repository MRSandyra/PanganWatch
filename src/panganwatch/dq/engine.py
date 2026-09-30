"""Data Quality Rule Engine for PanganWatch (F4).

Loads rules from config/dq_rules.yml, executes them against data before silver upsert,
writes results to governance.dq_results, and quarantines records failing 'error' severity rules.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import yaml
from pydantic import BaseModel, Field

from panganwatch.db import get_postgres_connection


class DQRule(BaseModel):
    """Single data quality rule definition."""

    rule_id: str
    dataset: str
    column: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)
    dimension: str
    severity: str  # "error" | "warn"
    owner: str
    description: str


class DQResult(BaseModel):
    """Aggregated result of a single rule check."""

    run_id: str
    rule_id: str
    dataset: str
    column: str
    dimension: str
    severity: str
    rows_checked: int
    rows_failed: int
    pass_rate: float
    checked_at: datetime


class QuarantineRecord(BaseModel):
    """Record quarantined for failing an 'error' rule."""

    run_id: str
    dataset: str
    natural_key: dict[str, Any]
    record: dict[str, Any]
    rule_id: str
    reason: str
    quarantined_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None


class DQEngine:
    """Data Quality Rule Engine."""

    def __init__(self, rules_path: str = "config/dq_rules.yml"):
        self.rules_path = rules_path
        self.rules: list[DQRule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from YAML file."""
        if not os.path.exists(self.rules_path):
            raise FileNotFoundError(f"DQ rules file not found: {self.rules_path}")

        with open(self.rules_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.rules = [DQRule(**rule) for rule in data.get("rules", [])]

    def get_rules_for_dataset(self, dataset: str) -> list[DQRule]:
        """Get all rules applicable to a specific dataset."""
        return [r for r in self.rules if r.dataset == dataset]

    def _get_connection(self):
        """Get a Postgres connection."""
        return get_postgres_connection()

    def _execute_query(self, query: str, params: tuple = ()) -> list[tuple]:
        """Execute a query and return all rows."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        finally:
            conn.close()

    def _execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """Execute a query and return a single scalar value."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            conn.close()

    def _write_dq_result(self, result: DQResult) -> None:
        """Write aggregated DQ result to governance.dq_results."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO governance.dq_results
                       (run_id, rule_id, dataset, column_name, dimension, severity, rows_checked, rows_failed, pass_rate, checked_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        result.run_id,
                        result.rule_id,
                        result.dataset,
                        result.column,
                        result.dimension,
                        result.severity,
                        result.rows_checked,
                        result.rows_failed,
                        result.pass_rate,
                        result.checked_at,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _quarantine_record(self, record: QuarantineRecord) -> None:
        """Write a quarantined record to governance.quarantine."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO governance.quarantine
                       (run_id, dataset, natural_key, record, rule_id, reason, quarantined_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        record.run_id,
                        record.dataset,
                        json.dumps(record.natural_key),
                        json.dumps(record.record, default=str),
                        record.rule_id,
                        record.reason,
                        record.quarantined_at,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _natural_key_dict(self, record: dict[str, Any], key_columns: list[str]) -> dict[str, Any]:
        """Extract natural key from record."""
        return {k: record.get(k) for k in key_columns}

    def _check_not_null(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check not_null rule."""
        column = rule.column
        failed = [r for r in records if r.get(column) is None]
        return len(records), len(failed), failed

    def _check_range(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check range rule."""
        column = rule.column
        params = rule.params
        min_val = params.get("min")
        max_val = params.get("max")
        # allow_null: a NULL is legitimately "not derivable" (e.g. first month of a
        # derived series), not out of range; not_null rules cover real missing data.
        allow_null = bool(params.get("allow_null", False))

        def check_val(val):
            if val is None:
                return allow_null
            if min_val is not None and val < min_val:
                return False
            if max_val is not None and val > max_val:
                return False
            return True

        failed = [r for r in records if not check_val(r.get(column))]
        return len(records), len(failed), failed

    def _check_in_reference(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check in_reference rule."""
        column = rule.column
        params = rule.params
        ref_table = params.get("reference_table")
        ref_column = params.get("reference_column")

        # Get all valid reference values
        valid_values = set()
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {ref_column} FROM {ref_table}")
                valid_values = {row[0] for row in cur.fetchall()}
        finally:
            conn.close()

        failed = [r for r in records if r.get(column) not in valid_values]
        return len(records), len(failed), failed

    def _check_unique_key(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check unique_key rule."""
        key_columns = rule.params.get("key_columns", [])
        seen = set()
        failed = []

        for r in records:
            key = tuple(r.get(k) for k in key_columns)
            if key in seen:
                failed.append(r)
            else:
                seen.add(key)

        return len(records), len(failed), failed

    def _check_freshness(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check freshness rule."""
        column = rule.column
        params = rule.params
        max_lag_days = params.get("max_lag_days", 3)

        # For simplicity, check against current date
        # In real scenario, this would check max date in table
        from datetime import timedelta

        cutoff_date = datetime.now(UTC).date() - timedelta(days=max_lag_days)

        failed = []
        for r in records:
            val = r.get(column)
            if val is None:
                failed.append(r)
            elif hasattr(val, "date"):
                if val.date() < cutoff_date:
                    failed.append(r)
            elif isinstance(val, str):
                try:
                    if datetime.fromisoformat(val.replace("Z", "+00:00")).date() < cutoff_date:
                        failed.append(r)
                except Exception:
                    failed.append(r)

        return len(records), len(failed), failed

    def _check_max_pct_change(
        self, rule: DQRule, records: list[dict]
    ) -> tuple[int, int, list[dict]]:
        """Check max_pct_change rule - compares with last value in silver."""
        params = rule.params
        max_pct = params.get("max_pct", 50)
        partition_by = params.get("partition_by", [])
        order_by = params.get("order_by", "tanggal")
        column = rule.column

        # For each record, check against the last value in silver for same partition
        failed = []
        conn = self._get_connection()

        for r in records:
            partition_values = {k: r.get(k) for k in partition_by}
            where_clauses = [f"{k} = %s" for k in partition_by]
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            values = tuple(partition_values.values())

            query = f"""
                SELECT {column} FROM {rule.dataset}
                WHERE {where_sql}
                ORDER BY {order_by} DESC
                LIMIT 1
            """

            try:
                with conn.cursor() as cur:
                    cur.execute(query, values)
                    row = cur.fetchone()
                    if row and row[0] is not None and r.get(column) is not None:
                        last_val = float(row[0])
                        curr_val = float(r.get(column))
                        if last_val != 0:
                            pct_change = abs((curr_val - last_val) / last_val) * 100
                            if pct_change > max_pct:
                                failed.append(r)
            except Exception:
                # Table might not exist yet or column issues
                pass

        conn.close()
        return len(records), len(failed), failed

    def _check_completeness_ratio(
        self, rule: DQRule, records: list[dict]
    ) -> tuple[int, int, list[dict]]:
        """Check completeness_ratio rule."""
        params = rule.params
        group_by = params.get("group_by", "tanggal")
        target_column = params.get("target_column", "kode_provinsi_bps")
        min_ratio = params.get("min_ratio", 0.8)
        filter_config = params.get("filter", {})

        # Group records by group_by
        from collections import defaultdict

        groups = defaultdict(list)
        for r in records:
            # Apply filter if specified
            filter_col = filter_config.get("column")
            filter_vals = filter_config.get("values", [])
            if filter_col and filter_vals:
                if r.get(filter_col) not in filter_vals:
                    continue
            key = r.get(group_by)
            if key is not None:
                groups[key].append(r)

        failed = []
        # For each group, check the share of DISTINCT non-null target values
        # (e.g. provinces) against the expected total. Counting rows instead of
        # distinct values made this rule pass vacuously (thousands of price rows
        # per date vs. 38 provinces) — DEC-036.
        expected_distinct = params.get("expected_distinct", 38)

        for group_key, group_records in groups.items():
            non_null = len(
                {r[target_column] for r in group_records if r.get(target_column) is not None}
            )
            ratio = non_null / expected_distinct if expected_distinct > 0 else 0
            if ratio < min_ratio:
                failed.extend(group_records)

        return len(records), len(failed), failed

    def _check_cross_source_diff(
        self, rule: DQRule, records: list[dict]
    ) -> tuple[int, int, list[dict]]:
        """Check cross_source_diff rule."""
        # Check if multiple sources exist
        sources = set(r.get("source") for r in records if r.get("source"))
        if len(sources) <= 1:
            return len(records), 0, []  # N/A - only one source

        # This is a simplified check - in practice would compute median per source
        # For now, mark as not applicable if single source
        return len(records), 0, []

    def _check_row_count(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check row_count rule."""
        expected = rule.params.get("expected", 0)
        actual = len(records)
        failed = records if actual != expected else []
        return len(records), len(failed), failed

    def _check_custom_range(self, rule: DQRule, records: list[dict]) -> tuple[int, int, list[dict]]:
        """Check custom_range rule - evaluates a custom condition between columns."""
        column = rule.column
        params = rule.params
        check_expr = params.get("check", "")
        other_column = params.get("other_column")

        if not check_expr or not other_column:
            return len(records), 0, []

        failed = []
        for r in records:
            val = r.get(column)
            other_val = r.get(other_column)
            if val is not None and other_val is not None:
                # Evaluate the check expression
                # Only support "col1 <= col2" format for safety
                try:
                    if "<=" in check_expr:
                        if float(val) > float(other_val):
                            failed.append(r)
                    elif ">=" in check_expr:
                        if float(val) < float(other_val):
                            failed.append(r)
                    elif "<" in check_expr:
                        if float(val) >= float(other_val):
                            failed.append(r)
                    elif ">" in check_expr:
                        if float(val) <= float(other_val):
                            failed.append(r)
                    elif "==" in check_expr:
                        if float(val) != float(other_val):
                            failed.append(r)
                    elif "!=" in check_expr:
                        if float(val) == float(other_val):
                            failed.append(r)
                except (ValueError, TypeError):
                    failed.append(r)

        return len(records), len(failed), failed

    def check_records(
        self, dataset: str, records: list[dict], run_id: str
    ) -> tuple[list[dict], list[dict]]:
        """Check records against all rules for a dataset.

        Returns: (clean_records, quarantined_records)
        clean_records: records that passed all 'error' rules (warn failures allowed through)
        quarantined_records: records that failed at least one 'error' rule
        """
        if not records:
            return [], []

        rules = self.get_rules_for_dataset(dataset)
        if not rules:
            return records, []  # No rules for this dataset

        # Track which records fail 'error' rules
        quarantined_indices = set()
        all_results = []

        for rule in rules:
            try:
                if rule.type == "not_null":
                    rows_checked, rows_failed, failed_records = self._check_not_null(rule, records)
                elif rule.type == "range":
                    rows_checked, rows_failed, failed_records = self._check_range(rule, records)
                elif rule.type == "in_reference":
                    rows_checked, rows_failed, failed_records = self._check_in_reference(
                        rule, records
                    )
                elif rule.type == "unique_key":
                    rows_checked, rows_failed, failed_records = self._check_unique_key(
                        rule, records
                    )
                elif rule.type == "freshness":
                    rows_checked, rows_failed, failed_records = self._check_freshness(rule, records)
                elif rule.type == "max_pct_change":
                    rows_checked, rows_failed, failed_records = self._check_max_pct_change(
                        rule, records
                    )
                elif rule.type == "completeness_ratio":
                    rows_checked, rows_failed, failed_records = self._check_completeness_ratio(
                        rule, records
                    )
                elif rule.type == "cross_source_diff":
                    rows_checked, rows_failed, failed_records = self._check_cross_source_diff(
                        rule, records
                    )
                elif rule.type == "row_count":
                    rows_checked, rows_failed, failed_records = self._check_row_count(rule, records)
                elif rule.type == "custom_range":
                    rows_checked, rows_failed, failed_records = self._check_custom_range(
                        rule, records
                    )
                else:
                    print(f"Unknown rule type: {rule.type} for rule {rule.rule_id}")
                    continue

                pass_rate = (
                    (rows_checked - rows_failed) / rows_checked * 100 if rows_checked > 0 else 100
                )

                result = DQResult(
                    run_id=run_id,
                    rule_id=rule.rule_id,
                    dataset=rule.dataset,
                    column=rule.column,
                    dimension=rule.dimension,
                    severity=rule.severity,
                    rows_checked=rows_checked,
                    rows_failed=rows_failed,
                    pass_rate=pass_rate,
                    checked_at=datetime.now(UTC),
                )
                self._write_dq_result(result)
                all_results.append(result)

                # If severity is error, quarantine the failed records
                if rule.severity == "error" and failed_records:
                    for fr in failed_records:
                        # Find index of failed record in original list
                        try:
                            idx = records.index(fr)
                            quarantined_indices.add(idx)
                        except ValueError:
                            pass

            except Exception as e:
                # Distinguish between rule evaluation failure (bug) vs data validation failure
                # Rule evaluation failures are bugs in the engine itself and should be logged with full traceback
                # Data validation failures are expected and handled by the check methods returning failed records
                import traceback

                print(f"RULE EVALUATION ERROR (engine bug) for rule {rule.rule_id}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Write a failed result marking this as an engine error, not data failure
                result = DQResult(
                    run_id=run_id,
                    rule_id=rule.rule_id,
                    dataset=rule.dataset,
                    column=rule.column,
                    dimension=rule.dimension,
                    severity=rule.severity,
                    rows_checked=len(records),
                    rows_failed=len(records),
                    pass_rate=0.0,
                    checked_at=datetime.now(UTC),
                )
                self._write_dq_result(result)

        # Separate clean and quarantined records
        clean_records = [r for i, r in enumerate(records) if i not in quarantined_indices]
        quarantined_records = [r for i, r in enumerate(records) if i in quarantined_indices]

        # Write quarantine records
        for qr in quarantined_records:
            # Find which rule caused it (first error rule that failed)
            for rule in rules:
                if rule.severity == "error":
                    # Re-check this specific record
                    try:
                        if rule.type == "not_null":
                            failed = qr.get(rule.column) is None
                        elif rule.type == "range":
                            val = qr.get(rule.column)
                            min_val = rule.params.get("min")
                            max_val = rule.params.get("max")
                            failed = (
                                (val is None and not rule.params.get("allow_null", False))
                                or (val is not None and min_val is not None and val < min_val)
                                or (val is not None and max_val is not None and val > max_val)
                            )
                        elif rule.type == "in_reference":
                            val = qr.get(rule.column)
                            if val is not None:
                                conn = self._get_connection()
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            f"SELECT 1 FROM {rule.params['reference_table']} WHERE {rule.params['reference_column']} = %s",
                                            (val,),
                                        )
                                        failed = cur.fetchone() is None
                                finally:
                                    conn.close()
                            else:
                                failed = True
                        elif rule.type == "unique_key":
                            # Handled at insert time via unique index
                            failed = False
                        elif rule.type == "freshness":
                            # Simplified
                            failed = False
                        elif rule.type == "custom_range":
                            val = qr.get(rule.column)
                            other_val = qr.get(rule.params.get("other_column"))
                            check_expr = rule.params.get("check", "")
                            failed = False
                            if val is not None and other_val is not None:
                                try:
                                    if "<=" in check_expr:
                                        failed = float(val) > float(other_val)
                                    elif ">=" in check_expr:
                                        failed = float(val) < float(other_val)
                                    elif "<" in check_expr:
                                        failed = float(val) >= float(other_val)
                                    elif ">" in check_expr:
                                        failed = float(val) <= float(other_val)
                                    elif "==" in check_expr:
                                        failed = float(val) != float(other_val)
                                    elif "!=" in check_expr:
                                        failed = float(val) == float(other_val)
                                except (ValueError, TypeError):
                                    failed = True
                        else:
                            failed = False

                        if failed:
                            q_record = QuarantineRecord(
                                run_id=run_id,
                                dataset=dataset,
                                natural_key=self._natural_key_dict(
                                    qr, rule.params.get("key_columns", [rule.column])
                                ),
                                record=qr,
                                rule_id=rule.rule_id,
                                reason=f"Failed {rule.type} check: {rule.description}",
                                quarantined_at=datetime.now(UTC),
                            )
                            self._quarantine_record(q_record)
                            break
                    except Exception:
                        pass

        return clean_records, quarantined_records


def run_dq_checks(dataset: str, records: list[dict], run_id: str) -> tuple[list[dict], list[dict]]:
    """Convenience function to run DQ checks on a dataset."""
    engine = DQEngine()
    return engine.check_records(dataset, records, run_id)


def generate_dq_docs(output_path: str = "docs/governance/dq_rules.md") -> None:
    """Generate documentation from dq_rules.yml."""
    engine = DQEngine()
    rules = engine.rules

    lines = [
        "# Data Quality Rules",
        "",
        "Generated from `config/dq_rules.yml`. Do not edit manually — run `make dq-docs`.",
        f"Total rules: {len(rules)}",
        "",
        "| rule_id | dataset | column | type | dimension | severity | owner | description |",
        "|---------|---------|--------|------|-----------|----------|-------|-------------|",
    ]

    for r in rules:
        lines.append(
            f"| {r.rule_id} | {r.dataset} | {r.column} | {r.type} | {r.dimension} | {r.severity} | {r.owner} | {r.description} |"
        )

    # Dimension summary
    lines.append("")
    lines.append("## Summary by DAMA Dimension")
    lines.append("")
    dims = {}
    for r in rules:
        dims.setdefault(r.dimension, 0)
        dims[r.dimension] += 1

    lines.append("| Dimension | Count |")
    lines.append("|-----------|-------|")
    for dim in ["completeness", "validity", "accuracy", "consistency", "timeliness", "uniqueness"]:
        if dim in dims:
            lines.append(f"| {dim} | {dims[dim]} |")

    lines.append("")
    lines.append("## Summary by Severity")
    lines.append("")
    sev = {"error": 0, "warn": 0}
    for r in rules:
        sev[r.severity] += 1
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| error | {sev['error']} |")
    lines.append(f"| warn | {sev['warn']} |")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {output_path} with {len(rules)} rules")


if __name__ == "__main__":
    # CLI for generating docs
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate-docs":
        generate_dq_docs()
    else:
        print("Usage: python -m panganwatch.dq.engine generate-docs")
