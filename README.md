# End-to-End Plan

## Scope & Domain

Scope: Create datawarehouse, from ETL to datacube.

Domain: Affordable Care Act (ACA) health insurance

## Source Data Setup (domain specific)

### health insurance

- Generate CSV seed data:
  - members
  - plans (with metal tier, premiums, coverage details)
  - providers
  - claims and enrollments

`python ./scripts/generate_seed_data.py`

## Staging Layer

- launch database
- define schema on load, with data dictionary

`docker compose -f infrastructure/docker/docker-compose.yml up`

## Load Staging Data

- Load seed CSVs into staging tables 1:1.
- No transforms — just type coercion + basic validation.
- Track load batch metadata:
  - `load_id`
  - `load_timestamp`

`python -m etl.load.staging_loader`

## Dimensional Modeling

ACA star schema:

Dimensions (SCD2 where noted):
- DimDate (static) – calendar attributes (date_key surrogate, date actual, year, month, etc.)
- DimMember (SCD2) – member demographics + socioeconomic & engagement attributes
  - Surrogate: member_sk (BIGINT)
  - Natural key: member_id
  - Change driver attributes (hash set): name, dob, gender, age_group, region, fpl_ratio, clinical_segment, broker/general_agency fields, engagement flags, high_cost_member, mutually_exclusive_hcc_condition, plan_metal, plan_network_access_type, geographic_reporting, year
- DimPlan (SCD2 yearly) – plan benefit & pricing attributes
  - Surrogate: plan_sk
  - Natural key: (plan_id, effective_year)
  - Change driver: name, metal_tier, monthly_premium, deductible, oop_max, coinsurance_rate, pcp_copay
- DimProvider (SCD2) – provider identity & specialty + location
  - Surrogate: provider_sk
  - Natural key: provider_id (optionally npi if guaranteed stable)
  - Change driver: name, specialty, street, city, state, zip, phone
- DimGeography (optional) – region / state rollups
  - Surrogate: geography_sk
  - Natural key: (state, region)
- DimEnrollment (Type 2 or factless bridge optional) – enrollment periods (if analytic slicing on coverage periods needed)
  - Surrogate: enrollment_sk
  - Natural key: (member_id, plan_id, start_date)
- DimClaimStatus / DimProcedure / DimDiagnosis (optional outriggers) if high cardinality reuse emerges; initially inline on fact.

Facts:
- FactEnrollment (grain: one row per member-plan continuous coverage period)
  - Grain: (member_sk, plan_sk, enrollment_start_date_key)
  - Measures: premium_paid (can be snapshot or accumulated), coverage_days
- FactClaim (primary fact)
  - Grain: one claim line (current generator produces claim-level; can extend to line-level later). For now: one row per claim_id
  - Natural business key: claim_id
  - Foreign keys: date_key (service_date), member_sk, provider_sk, plan_sk
  - Degenerate: claim_id
  - Attributes kept (or normalized later): status, diagnosis_code, procedure_code
  - Measures: claim_amount, allowed_amount, paid_amount

Surrogate Keys & SCD2 Columns (for applicable dims):
- Each SCD2 dimension table columns: *_sk (PK), natural key columns, validity_start_ts, validity_end_ts, current_flag (BOOLEAN), attr_hash (TEXT / BYTEA), load_id, created_at
- validity_end_ts = '9999-12-31'::timestamp for current row
- Unique index: (natural_key_columns, validity_start_ts)
- Current row fast lookup index: (natural_key_columns) WHERE current_flag

Grains Summary:
- DimMember: one row per member version
- DimPlan: one row per plan_id + effective_year version
- DimProvider: one row per provider version
- FactClaim: claim_id (event-level) – can be extended to claim line if line_number added
- FactEnrollment: member-plan enrollment period

Change Detection Approach:
1. Stage raw into staging.*_raw (done)
2. Compute attr_hash = stable hash (e.g. SHA256 concat of ordered change driver attributes after normalization)
3. For each natural key:
   - If no current row: insert new version
   - If current exists AND hash differs: update current row (set validity_end_ts = now, current_flag = false) then insert new row
   - Else skip

Future Optional Dimensions:
- DimBroker (if broker attributes explode)
- DimClinicalSegment (if needing classification history) – else remain attribute on DimMember

Open Questions / To Decide:
- Whether to separate Address dimension for providers & members (likely premature)
- Add Date dimension generation script or SQL? (simple calendar table)
- Claim line modeling (introduce line_number for multi-line claims)

## ETL Pipelines

- **Extract**: Read CSV
- **Transform**:
  - Standardize types
  - Trim strings
  - Deduplicate
  - Conform dimensions (slowly changing attributes list)
- **Load**:
  - Upsert dimensions (use SCD Type 2 for Member, Plan, Provider)
  - Insert facts referencing current dimension surrogate keys
  - Add data quality checks:
    - Row counts
    - Null checks
    - Referential integrity
    - Duplicate natural keys

## Slowly Changing Dimensions

- Implement helper for SCD2:
  - Detect changes via hashed attribute set
  - Expire old row (`end_date`)
  - Insert new row (`start_date`, `current_flag`)

## Aggregations / Cubes

- Create summary tables or materialized views:
  - claims_daily_member (sum claim + paid amounts)
  - claims_by_plan_metal_month
  - high_cost_member_tracking (rolling 12m)
  - utilization_by_specialty
- Optionally build a small OLAP-like layer using:
  - DuckDB
  - Postgres materialized views

## Automation & Orchestration

- Provide `run.py` to execute:
  - extract -> stage -> dims -> facts -> aggregates
- Add incremental load simulation (new timestamped seed sets) to test SCD2 logic

## Testing & Validation

- Unit tests for transform functions
- Data quality assertions:
  - Use `great_expectations` or custom checks
- Row count reconciliation:
  - Staged vs loaded facts

## Performance & Optimization (Optional)

- Add indexes on foreign keys and date
- Partition large fact table by date (if using Postgres)

## Documentation

- Docs handled via sphinx, sent to readthedocs via Github Action.

- Update `README` with:
  - Mermaid schema diagram
  - Load sequence
  - Sample queries

### Automation (Makefile-Centric)
Makefile is the single interface for: environment bootstrap, linting, tests, data generation, full vs incremental loads, data quality checks, and container lifecycle.

Core concepts:
- Phony targets map to logical pipeline stages.
- Full load vs incremental controlled by flags/targets.
- Environment variables loaded from .env / config/dev.env.
- Docker Compose spins up Postgres (and optional helpers).

### Tech (optional)
- data creation: faker?
- Packaging: uv
- Env management: python-dotenv
- linting python: Ruff
- linting sql: SQLFluff
- DB migrations: Alembic
- Transform modeling (SQL focus): dbt (optional)
- Data quality: Great Expectations
- Containerization: Docker + docker-compose (local Postgres)
- Logging: structlog / standard lib + JSON formatting
- Hashing for SCD2: xxhash / hashlib

### Next Steps
- Build dimension DDL (DimMember, DimPlan, DimProvider, DimDate, optional DimGeography)
- Implement attr hash + SCD2 upsert routines
- Add fact loaders (claims, enrollment)
- Add calendar population script
- Data quality SQL tests (PK, FK, null, duplicates, row counts)
- Add pre-commit for formatting & lint gating.



