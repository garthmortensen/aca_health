-- Data Warehouse (dw) schema DDL
-- Creates dimensional & fact tables per ADR 0001 baseline design.
-- Idempotent (IF NOT EXISTS) so file can be re-run safely.

-- Schema
CREATE SCHEMA IF NOT EXISTS dw;

-- Explicit surrogate key sequences
CREATE SEQUENCE IF NOT EXISTS dw.sk_member_seq;
CREATE SEQUENCE IF NOT EXISTS dw.sk_provider_seq;
CREATE SEQUENCE IF NOT EXISTS dw.sk_plan_seq;
CREATE SEQUENCE IF NOT EXISTS dw.sk_date_seq;

-- ============================================================================
-- Dimensions
-- ============================================================================

-- Date Dimension
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key        INTEGER PRIMARY KEY,              -- yyyymmdd integer (e.g., 20250131)
    full_date       DATE NOT NULL UNIQUE,
    year            INTEGER NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      TEXT,
    day             SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,                -- 1=Monday .. 7=Sunday (ISO)
    day_name        TEXT,
    week_of_year    SMALLINT,                         -- ISO week number
    is_weekend      BOOLEAN NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Member Dimension (SCD2)
CREATE TABLE IF NOT EXISTS dw.dim_member (
    member_sk           BIGINT PRIMARY KEY DEFAULT nextval('dw.sk_member_seq'),
    member_id           TEXT NOT NULL,           -- natural key
    first_name          TEXT,
    last_name           TEXT,
    dob                 DATE,
    gender              CHAR(1),
    email               TEXT,
    phone               TEXT,
    street              TEXT,
    city                TEXT,
    state               CHAR(2),
    zip                 TEXT,
    federal_poverty_level_ratio NUMERIC(5,2),
    plan_network_access_type TEXT,
    plan_metal          TEXT,
    age_group           TEXT,
    region              TEXT,
    enrollment_length_continuous SMALLINT,
    clinical_segment    TEXT,
    general_agency_name TEXT,
    broker_name         TEXT,
    sa_contracting_entity_name TEXT,
    new_member_in_period SMALLINT,
    member_used_app     SMALLINT,
    member_had_web_login SMALLINT,
    member_visited_new_provider_ind SMALLINT,
    high_cost_member    SMALLINT,
    mutually_exclusive_hcc_condition TEXT,
    geographic_reporting TEXT,
    year                INTEGER,
    -- SCD2 metadata
    validity_start_ts   TIMESTAMPTZ NOT NULL DEFAULT now(),
    validity_end_ts     TIMESTAMPTZ NOT NULL DEFAULT '9999-12-31',
    current_flag        BOOLEAN NOT NULL DEFAULT TRUE,
    attr_hash           CHAR(64) NOT NULL,           -- SHA256 of business attrs for change detection
    load_id             BIGINT,                      -- staging.load_batches reference
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (member_id, validity_start_ts)
);
CREATE INDEX IF NOT EXISTS idx_dim_member_member_id_current ON dw.dim_member(member_id) WHERE current_flag;
CREATE INDEX IF NOT EXISTS idx_dim_member_attr_hash_current ON dw.dim_member(attr_hash) WHERE current_flag;

-- Provider Dimension (SCD2)
CREATE TABLE IF NOT EXISTS dw.dim_provider (
    provider_sk        BIGINT PRIMARY KEY DEFAULT nextval('dw.sk_provider_seq'),
    provider_id        TEXT NOT NULL,      -- natural key
    npi                TEXT,
    name               TEXT,
    specialty          TEXT,
    street             TEXT,
    city               TEXT,
    state              CHAR(2),
    zip                TEXT,
    phone              TEXT,
    -- SCD2 metadata
    validity_start_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),
    validity_end_ts    TIMESTAMPTZ NOT NULL DEFAULT '9999-12-31',
    current_flag       BOOLEAN NOT NULL DEFAULT TRUE,
    attr_hash          CHAR(64) NOT NULL,
    load_id            BIGINT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider_id, validity_start_ts)
);
CREATE INDEX IF NOT EXISTS idx_dim_provider_provider_id_current ON dw.dim_provider(provider_id) WHERE current_flag;

-- Plan Dimension (SCD2) - natural key (plan_id, effective_year)
CREATE TABLE IF NOT EXISTS dw.dim_plan (
    plan_sk            BIGINT PRIMARY KEY DEFAULT nextval('dw.sk_plan_seq'),
    plan_id            TEXT NOT NULL,
    name               TEXT,
    metal_tier         TEXT,
    monthly_premium    NUMERIC(10,2),
    deductible         INTEGER,
    oop_max            INTEGER,
    coinsurance_rate   NUMERIC(5,4),
    pcp_copay          INTEGER,
    effective_year     INTEGER NOT NULL,
    -- SCD2 metadata
    validity_start_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),
    validity_end_ts    TIMESTAMPTZ NOT NULL DEFAULT '9999-12-31',
    current_flag       BOOLEAN NOT NULL DEFAULT TRUE,
    attr_hash          CHAR(64) NOT NULL,
    load_id            BIGINT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plan_id, effective_year, validity_start_ts)
);
CREATE INDEX IF NOT EXISTS idx_dim_plan_nk_current ON dw.dim_plan(plan_id, effective_year) WHERE current_flag;

-- ============================================================================
-- Fact Tables
-- ============================================================================

-- Claim Fact (one row per claim_id)
CREATE TABLE IF NOT EXISTS dw.fact_claim (
    claim_id        TEXT NOT NULL,
    member_sk       BIGINT NOT NULL REFERENCES dw.dim_member(member_sk),
    provider_sk     BIGINT NOT NULL REFERENCES dw.dim_provider(provider_sk),
    plan_sk         BIGINT NOT NULL REFERENCES dw.dim_plan(plan_sk),
    date_key        INTEGER NOT NULL REFERENCES dw.dim_date(date_key),
    service_date    DATE NOT NULL,
    claim_amount    NUMERIC(12,2),
    allowed_amount  NUMERIC(12,2),
    paid_amount     NUMERIC(12,2),
    status          TEXT,
    diagnosis_code  TEXT,
    procedure_code  TEXT,
    load_id         BIGINT,                      -- from staging.claims_raw
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (claim_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_claim_member_sk ON dw.fact_claim(member_sk);
CREATE INDEX IF NOT EXISTS idx_fact_claim_provider_sk ON dw.fact_claim(provider_sk);
CREATE INDEX IF NOT EXISTS idx_fact_claim_plan_sk ON dw.fact_claim(plan_sk);
CREATE INDEX IF NOT EXISTS idx_fact_claim_date_key ON dw.fact_claim(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_claim_status ON dw.fact_claim(status);

-- Enrollment Fact (one row per continuous enrollment period)
CREATE TABLE IF NOT EXISTS dw.fact_enrollment (
    enrollment_id   TEXT NOT NULL,                -- natural key
    member_sk       BIGINT NOT NULL REFERENCES dw.dim_member(member_sk),
    plan_sk         BIGINT NOT NULL REFERENCES dw.dim_plan(plan_sk),
    start_date_key  INTEGER NOT NULL REFERENCES dw.dim_date(date_key),
    end_date_key    INTEGER NOT NULL REFERENCES dw.dim_date(date_key),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    premium_paid    NUMERIC(10,2),
    csr_variant     TEXT,
    coverage_days   INTEGER,
    load_id         BIGINT,                      -- from staging.enrollments_raw
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (enrollment_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_enrollment_member_sk ON dw.fact_enrollment(member_sk);
CREATE INDEX IF NOT EXISTS idx_fact_enrollment_plan_sk ON dw.fact_enrollment(plan_sk);
CREATE INDEX IF NOT EXISTS idx_fact_enrollment_start_date_key ON dw.fact_enrollment(start_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_enrollment_end_date_key ON dw.fact_enrollment(end_date_key);

-- ============================================================================
-- Helper views for current dimension rows
-- ============================================================================
CREATE OR REPLACE VIEW dw.v_dim_member_current AS
SELECT * FROM dw.dim_member WHERE current_flag = TRUE;

CREATE OR REPLACE VIEW dw.v_dim_provider_current AS
SELECT * FROM dw.dim_provider WHERE current_flag = TRUE;

CREATE OR REPLACE VIEW dw.v_dim_plan_current AS
SELECT * FROM dw.dim_plan WHERE current_flag = TRUE;
