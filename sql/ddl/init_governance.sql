-- create table if not exists
CREATE TABLE IF NOT EXISTS governance.pipeline_runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    source text NOT NULL,
    status text NOT NULL,
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    rows_processed int,
    rows_success int,
    rows_failed int,
    error_message text
);

CREATE TABLE IF NOT EXISTS governance.dq_results (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    rule_id text NOT NULL,
    dataset text NOT NULL,
    column_name text NOT NULL,
    dimension text NOT NULL,
    severity text NOT NULL,
    rows_checked int NOT NULL,
    rows_failed int NOT NULL,
    pass_rate numeric(5,2) NOT NULL,
    checked_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance.quarantine (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL,
    dataset text NOT NULL,
    natural_key jsonb NOT NULL,
    record jsonb NOT NULL,
    rule_id text NOT NULL,
    reason text NOT NULL,
    quarantined_at timestamptz DEFAULT now(),
    resolved_at timestamptz,
    resolution_note text
);

-- dbt seeds (ref.ref_provinsi, ref.ref_komoditas) don't declare DB-level unique
-- constraints; add them so silver tables below can FK-reference kode_bps /
-- komoditas_id. Runs only after `dbt seed` has created these tables.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ref' AND table_name = 'ref_provinsi') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ref_provinsi_kode_bps_key') THEN
            ALTER TABLE ref.ref_provinsi ADD CONSTRAINT ref_provinsi_kode_bps_key UNIQUE (kode_bps);
        END IF;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ref' AND table_name = 'ref_komoditas') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ref_komoditas_komoditas_id_key') THEN
            ALTER TABLE ref.ref_komoditas ADD CONSTRAINT ref_komoditas_komoditas_id_key UNIQUE (komoditas_id);
        END IF;
    END IF;
END
$$;

-- F3a: silver.harga_pangan (harga pangan harian per provinsi x komoditas x jenis pasar x source)
CREATE TABLE IF NOT EXISTS silver.harga_pangan (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tanggal date NOT NULL,
    kode_provinsi_bps varchar(2) NOT NULL REFERENCES ref.ref_provinsi (kode_bps),
    kode_kabkota_bps varchar(6),
    komoditas_id varchar(4) NOT NULL REFERENCES ref.ref_komoditas (komoditas_id),
    jenis_pasar text NOT NULL,
    harga numeric(12, 2) NOT NULL,
    satuan text NOT NULL,
    source text NOT NULL,
    run_id text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_harga_pangan_natural_key
    ON silver.harga_pangan (tanggal, kode_provinsi_bps, COALESCE(kode_kabkota_bps, ''), komoditas_id, jenis_pasar, source);

-- F3c: silver.cuaca_harian (cuaca historis harian per provinsi, Open-Meteo Archive API)
CREATE TABLE IF NOT EXISTS silver.cuaca_harian (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tanggal date NOT NULL,
    kode_provinsi_bps varchar(2) NOT NULL REFERENCES ref.ref_provinsi (kode_bps),
    precipitation_mm numeric(6, 2),
    tmax_c numeric(5, 2),
    tmin_c numeric(5, 2),
    source text NOT NULL DEFAULT 'open-meteo',
    run_id text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_cuaca_harian_natural_key
    ON silver.cuaca_harian (tanggal, kode_provinsi_bps);

-- F3b: silver.inflasi_kota (monthly IHK and inflation per BPS IHK city, BPS WebAPI var 2245/2249).
-- Natural key (bulan, kode_vervar): kode_vervar is the city id in the BPS variable (not a
-- region code); the city -> kab/kota -> province mapping is done in dbt via the ref_ihk_kota seed.
CREATE TABLE IF NOT EXISTS silver.inflasi_kota (
    bulan date NOT NULL,
    kode_vervar integer NOT NULL,
    nama_kota text NOT NULL,
    ihk numeric(10, 2) NOT NULL,
    inflasi_mtm numeric(8, 2),
    inflasi_yoy numeric(8, 2),
    source text NOT NULL DEFAULT 'BPS',
    run_id text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (bulan, kode_vervar)
);

-- Grant access to the dbt user
grant all privileges on schema governance to dbt_user;
grant all privileges on schema silver to dbt_user;
grant all privileges on schema gold to dbt_user;
grant all privileges on schema ref to dbt_user;

-- F6: silver.cuaca_terkini (cuaca terkini per provinsi, streaming Open-Meteo)
CREATE TABLE IF NOT EXISTS silver.cuaca_terkini (
    kode_provinsi_bps TEXT NOT NULL REFERENCES ref.ref_provinsi (kode_bps),
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c REAL,
    precipitation_mm REAL,
    humidity_pct REAL,
    wind_speed_kph REAL,
    wind_direction_deg REAL,
    cloud_cover_pct REAL,
    visibility_km REAL,
    pressure_hpa REAL,
    uv_index INTEGER,
    sunrise_at TIMESTAMPTZ,
    sunset_at TIMESTAMPTZ,
    moon_phase REAL,
    PRIMARY KEY (kode_provinsi_bps, observed_at)
);

-- F6: governance.weather_alerts
CREATE TABLE IF NOT EXISTS governance.weather_alerts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id TEXT NOT NULL,
    kode_provinsi_bps TEXT NOT NULL REFERENCES ref.ref_provinsi (kode_bps),
    alert_type TEXT NOT NULL,
    alert_level TEXT NOT NULL,
    threshold_field TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    current_value REAL NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- F6: governance.dlq_logs
CREATE TABLE IF NOT EXISTS governance.dlq_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id TEXT NOT NULL,
    original_topic TEXT NOT NULL,
    original_partition INTEGER,
    original_offset BIGINT,
    error_reason TEXT NOT NULL,
    raw_message JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dlq_logs_received_at ON governance.dlq_logs (received_at);
