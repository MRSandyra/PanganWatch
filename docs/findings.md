# PanganWatch Findings

Inflation source: BPS WebAPI (var 2245 IHK, var 2249 Y-on-Y inflation; 150 kab/kota, 2024-01 through 2026-08, 4,800 rows in `silver.inflasi_kota`).
Price source: HDX WFP, monthly, window 2025-06-15 through 2026-06-15 (13 monthly points, 20,864 rows, 8 commodities, 34 provinces).
Price data is monthly, so the "weekly variation" in the `avg_weekly_cv_pct` column is actually one bucket per month.

## 1. Largest price disparity: shallots, chicken eggs, and chicken meat — consistently in Maluku Utara and Sumatera Barat

`disparity.py` (last 3 available months, Apr–Jun 2026, 808 mart rows, 34 provinces) shows the largest average deviation from the national median:

| Commodity | Province | Average deviation | Cross-province CV (per month) |
|---|---|---|---|
| shallot / bawang merah (0104) | Maluku Utara (82) | +51.45% | 17.52% |
| garlic / bawang putih (0105) | Maluku Utara (82) | +47.73% | 16.54% |
| chicken egg / telur ayam (0107) | Maluku Utara (82) | +44.52% | 12.85% |
| chicken meat / daging ayam (0111) | Sumatera Barat (13) | +32.42% | 14.66% |
| rice / beras (0101) | Sumatera Barat (13) | +21.32% | 8.58% |

Sugar / gula pasir (0109) is the most uniform across provinces (CV 4.76%). Note: only 3 monthly observations per province, and **chili is absent from the data** (see finding 5), so no claim can be made about "chili".

## 2. Heavy rain shows no relationship with shallot prices distinguishable from chance

`weather_price_lag.py` (2,490 rows of `mart_cuaca_harga_bulanan`, 34 provinces, 2025-06 through 2026-06; groups: shallot, rice, meat, sugar, oil, egg):

- Of 144 province×group×lag combinations tested, **6 (4.2%)** have p < 0.1. Under the null hypothesis, ~14.4 combinations (10% × 144) would clear that threshold by chance alone — so 6 is not evidence of a relationship.
- Strongest: Kalimantan Selatan (63), shallot, 3-month lag, Spearman ρ = −0.8281 (p = 0.0418, **n = 6** — very small).
- Pooled across all provinces, shallot: lag 1 ρ = 0.0028 (p = 0.957, n = 381); lag 2 ρ = 0.1012 (p = 0.0596, n = 347); lag 3 ρ = −0.0426 (p = 0.453, n = 313); lag 4 ρ = −0.0654 (p = 0.276, n = 279).
- Average heavy-rain days per province-month are only 0.14–0.16 (`x_mean` in `weather_price_lag_overall.csv`; very low variation).

This is **correlation, not causation**; confounders: harvest season, holidays, import policy, logistics, regional variation. Only shallot could be tested (not chili).

## 3. Data quality: the real problem is coverage, not values

The DQ engine was run against all of `silver.harga_pangan` (20,864 rows) and `silver.cuaca_harian` (≥17,708 rows): **0 records quarantined**, every value rule (not_null, range, referential, uniqueness, tmin ≤ tmax) passes 100%. The `warn`-severity coverage rules found issues (every figure checked with a separate query):

- `HP-014` (38-province coverage per month) **fails on all 13 months**: only 34/38 = **89.47%** of provinces have prices.
- `HP-012` (≥80% of provinces for rice/shallot) fails in one month: **2026-01-15**, only 8 provinces and 350 rows (other months have 33–34 provinces, 1,660–1,719 rows); **88 rows** of rice+shallot are flagged (exact match with a direct `count(*)`).
- The old coverage rules passed vacuously due to a bug (counting rows, using a fake commodity id) — fixed, DEC-036, `incident_log.md` Incident 4.

## 4. The DQ score history records a since-fixed CH-007 rule incident

Run `5cdd640c-…` (2026-09-23 09:23) in `governance.dq_results`: 17,708 of 141,664 row-checks failed (**12.50%**), entirely from one rule (CH-007, tmin ≤ tmax; 0 failures on any other rule). The cause was an implementation bug (a virtual column `tmin_tmax_order` that didn't exist), not bad data: `SELECT count(*) FROM silver.cuaca_harian WHERE tmin_c > tmax_c` = 0. After the fix, CH-007 fails 0 of 17,708. See `docs/governance/incident_log.md` Incident 1.

## 5. Data coverage: 34 of 38 provinces, 8 of 14 commodities, one nearly-empty month

- **Provinces:** 34 of 38. No price data for: Papua Selatan (93), Papua Tengah (94), Papua Pegunungan (95), Papua Barat Daya (96) — provinces created by the 2022 split that don't appear in HDX WFP (the raw file only has 34 `admin1` names). `dim_provinsi.csv` has 38. The national median is the median of 34 provinces.
- **Commodities:** only 8 of 14 reference commodities have prices (rice, shallot, garlic, beef, chicken egg, cooking oil, sugar, chicken meat). **Chili (3 varieties) is absent**: HDX WFP's chili rows stop on 2024-05-15, zero rows in the 2025-06..2026-06 window.
- **Time:** January 2026 in the source is already partial (346 raw rows, 8 provinces, vs. ~1,700 rows in other months); those 8 provinces are Bali, Jawa Tengah, Jawa Timur, Kalimantan Timur, Papua, Papua Barat, Sumatera Barat, and Sumatera Utara.
- Impact: month-over-month comparisons involving January 2026 are not on equal footing; business question 2 can only be answered for shallots.

## 6. City inflation (BPS) vs. food price change: a weak, positive, month-to-month unstable correlation

`inflation_food.py` combines `mart_inflasi_vs_harga` (monthly BPS IHK per city, mapped to province via `ref_ihk_kota`: 150/150 cities -> 38 provinces) with the HDX WFP food-price change (average of 8 commodities, vs. the previous calendar month). City inflation is averaged to province×month to avoid pseudo-replication:

- Pooled province×month: Spearman ρ = 0.206 (n = 354, p = 9.4e-05); excluding Jan–Feb 2026: ρ = 0.209 (n = 338, p = 0.000111).
- National monthly average series: ρ = 0.308 (n = 12, p = 0.33 — not significant).
- Monthly cross-sections: ρ ranges from −0.37 to +0.64; only 4 of 12 months have p < 0.05, with a mixed sign (2025-09 −0.37; 2025-10 +0.64; 2025-11 +0.44; 2026-03 +0.36).
- Level: the unweighted average year-on-year inflation across 150 cities is 1.57% (Dec 2024) -> 3.18% (Dec 2025) -> 3.42% (Aug 2026); 9 cities exceed 5% in Aug 2026 (highest: Kab. Kapuas 6.20%, Kota Ternate 5.75%).

This is **correlation, not causation**. Limitations: food prices cover only 8 commodities and only 2025-06 through 2026-06 (Jan–Feb 2026 has only 8 provinces), whereas the IHK covers the whole consumption basket; the 4 newly split Papua provinces (93–96) have IHK cities but no price data. Month-over-month inflation is derived from consecutive IHK values (BPS provides no M-to-M series for the 150 cities), and is NULL when the previous month is missing. Confounders: harvest season, holidays, fuel prices, policy.
