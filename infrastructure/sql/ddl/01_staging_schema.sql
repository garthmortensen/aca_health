-- Create staging schema
CREATE SCHEMA IF NOT EXISTS staging;

-- Load batch tracking table
CREATE TABLE IF NOT EXISTS staging.load_batches (
    load_id       BIGSERIAL PRIMARY KEY,
    source_name   TEXT NOT NULL,
    description   TEXT,
    file_pattern  TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    row_count     BIGINT,
    status        TEXT NOT NULL DEFAULT 'started' -- started|completed|failed
);

-- Plans raw
CREATE TABLE IF NOT EXISTS staging.plans_raw (
    plan_id           TEXT,
    name              TEXT,
    metal_tier        TEXT,
    monthly_premium   NUMERIC(10,2),
    deductible        INTEGER,
    oop_max           INTEGER,
    coinsurance_rate  NUMERIC(5,4),
    pcp_copay         INTEGER,
    effective_year    INTEGER,
    load_id           BIGINT REFERENCES staging.load_batches(load_id),
    load_timestamp    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Providers raw
CREATE TABLE IF NOT EXISTS staging.providers_raw (
    provider_id   TEXT,
    npi           TEXT,
    name          TEXT,
    specialty     TEXT,
    street        TEXT,
    city          TEXT,
    state         CHAR(2),
    zip           TEXT,
    phone         TEXT,
    load_id       BIGINT REFERENCES staging.load_batches(load_id),
    load_timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Members raw
CREATE TABLE IF NOT EXISTS staging.members_raw (
    member_id    TEXT,
    first_name   TEXT,
    last_name    TEXT,
    dob          DATE,
    gender       CHAR(1),
    email        TEXT,
    phone        TEXT,
    street       TEXT,
    city         TEXT,
    state        CHAR(2),
    zip          TEXT,
    fpl_ratio    NUMERIC(5,2),
    hios_id                              TEXT,
    plan_network_access_type             TEXT,
    plan_metal                           TEXT,
    age_group                            TEXT,
    region                               TEXT,
    enrollment_length_continuous         SMALLINT,
    clinical_segment                     TEXT,
    general_agency_name                  TEXT,
    broker_name                          TEXT,
    sa_contracting_entity_name           TEXT,
    new_member_in_period                 SMALLINT,
    member_used_app                      SMALLINT,
    member_had_web_login                 SMALLINT,
    member_visited_new_provider_ind      SMALLINT,
    high_cost_member                     SMALLINT,
    mutually_exclusive_hcc_condition     TEXT,
    geographic_reporting                 TEXT,
    year                                 INTEGER,
    load_id      BIGINT REFERENCES staging.load_batches(load_id),
    load_timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enrollments raw
CREATE TABLE IF NOT EXISTS staging.enrollments_raw (
    enrollment_id  TEXT,
    member_id      TEXT,
    plan_id        TEXT,
    start_date     DATE,
    end_date       DATE,
    premium_paid   NUMERIC(10,2),
    csr_variant    TEXT,
    load_id        BIGINT REFERENCES staging.load_batches(load_id),
    load_timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Claims raw
CREATE TABLE IF NOT EXISTS staging.claims_raw (
    claim_id        TEXT,
    member_id       TEXT,
    provider_id     TEXT,
    plan_id         TEXT,
    service_date    DATE,
    claim_amount    NUMERIC(12,2),
    allowed_amount  NUMERIC(12,2),
    paid_amount     NUMERIC(12,2),
    status          TEXT,
    diagnosis_code  TEXT,
    procedure_code  TEXT,
    load_id         BIGINT REFERENCES staging.load_batches(load_id),
    load_timestamp  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_plans_raw_load ON staging.plans_raw(load_id);
CREATE INDEX IF NOT EXISTS idx_providers_raw_load ON staging.providers_raw(load_id);
CREATE INDEX IF NOT EXISTS idx_members_raw_load ON staging.members_raw(load_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_raw_load ON staging.enrollments_raw(load_id);
CREATE INDEX IF NOT EXISTS idx_claims_raw_load ON staging.claims_raw(load_id);
CREATE INDEX IF NOT EXISTS idx_claims_raw_member ON staging.claims_raw(member_id);
CREATE INDEX IF NOT EXISTS idx_claims_raw_provider ON staging.claims_raw(provider_id);
CREATE INDEX IF NOT EXISTS idx_claims_raw_plan ON staging.claims_raw(plan_id);
CREATE INDEX IF NOT EXISTS idx_claims_raw_service_date ON staging.claims_raw(service_date);
-- Support idempotent re-runs: only one completed batch per file_pattern (optional semantic key)
CREATE UNIQUE INDEX IF NOT EXISTS uq_load_batches_file_pattern_completed
    ON staging.load_batches(file_pattern) WHERE status = 'completed';
