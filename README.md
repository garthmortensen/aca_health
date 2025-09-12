# End-to-End Plan

Scope: Create datawarehouse, from raw to semantic layer.

Domain: Affordable Care Act (ACA) health insurance

## [Data Dictionary](https://garthmortensen.github.io/aca_health/)

# aca_health
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

`python scripts/staging_loader.py`

### Tools

- Containerization: Docker + docker-compose
- Packaging: uv
- Transform modeling: dbt
- Data quality: Great Expectations / dbt_expectations
- data creation: faker
- linting: Ruff, SQLFluff
