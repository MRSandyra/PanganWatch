# Data contracts

Explicit Silver contracts are defined in `databricks/src/schemas.py`; inferred schemas are not used for curated tables.

| Dataset | Business key | Important contract |
|---|---|---|
| `harga_pangan` | date, province, nullable kab/kota, commodity, market, source | `harga DECIMAL(12,2)` |
| `cuaca_harian` | date, province | precipitation and temperature Decimal contracts |
| `inflasi_kota` | month, BPS city code | IHK and inflation decimal contracts |

`databricks/src/silver.py` resolves duplicate source records before Delta MERGE using ingestion timestamp then source checksum. Schema changes must be reviewed explicitly; unexpected fields are not silently added to Silver.
