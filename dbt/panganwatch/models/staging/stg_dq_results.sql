{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    id,
    run_id,
    rule_id,
    dataset,
    dimension,
    severity,
    rows_checked,
    rows_failed,
    pass_rate,
    checked_at
FROM {{ source('governance', 'dq_results') }}
