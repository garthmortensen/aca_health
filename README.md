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

## next steps

- Load seed CSVs into staging tables 1:1.
- No transforms — just type coercion + basic validation.
- Track load batch metadata:
  - `load_id`
  - `load_timestamp`

`python -m etl.load.staging_loader`

## Dimensional Modeling

- Design star schema:
  - FactSales
  - DimDate
  - DimCustomer
  - DimProduct
  - DimStore
  - DimGeography (optional)
- Define:
  - Surrogate keys
  - Natural keys
  - Grain: `(date_id, product_id, customer_id, store_id, transaction_id, line_number)`

## ETL Pipelines

- **Extract**: Read CSV
- **Transform**:
  - Standardize types
  - Trim strings
  - Deduplicate
  - Conform dimensions (slowly changing attributes list)
- **Load**:
  - Upsert dimensions (use SCD Type 2 for Customer and Product)
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
  - `sales_daily_product_store`
  - `sales_monthly_customer`
  - `product_performance` (rolling 30d, YoY)
- Optionally build a small OLAP-like layer using:
  - DuckDB
  - Postgres materialized views

## Automation & Orchestration

- Provide `run.py` to execute:
  - extract -> stage -> dims -> facts -> aggregates
- Add incremental load simulation (append daily sales file)

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
- Add requirements.txt & minimal run.py pipeline skeleton.
- Implement db connect helper (connection pool + retry).
- Build seed data generator + first staging load script.
- Add dimension loaders w/ SCD2 helper + hashing.
- Implement fact loader + basic aggregates.
- Add data quality scripts + sql tests (row counts, null, fk).
- Integrate db migrations (Alembic) & reference in Makefile.
- Add pre-commit for formatting & lint gating.



