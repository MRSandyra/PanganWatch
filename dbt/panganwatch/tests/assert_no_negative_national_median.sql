-- Singular test: the national median price must never be negative.
-- Passes if this query returns 0 rows.
SELECT *
FROM {{ ref('mart_disparitas_provinsi') }}
WHERE harga_median_nasional < 0
