{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- The "source" in Appendix B's grain maps to the `dataset` column in
-- governance.dq_results (e.g. "silver.harga_pangan"), because dq_results
-- logs results per dataset checked, not per ingestion source.
SELECT
    checked_at::date AS tanggal_run,
    dataset AS source,
    dimension AS dimensi,
    COUNT(DISTINCT rule_id) AS rules_total,
    COUNT(DISTINCT rule_id) FILTER (WHERE rows_failed = 0) AS rules_passed,
    SUM(rows_checked) AS rows_checked,
    SUM(rows_failed) AS rows_failed,
    ROUND(100.0 * (SUM(rows_checked) - SUM(rows_failed)) / NULLIF(SUM(rows_checked), 0), 2) AS score
FROM {{ ref('stg_dq_results') }}
GROUP BY 1, 2, 3
