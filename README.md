# aca_health

## overview

Create datawarehouse, from raw to semantic layer, to serve as foundation for cost analyzer.

[Data Dictionary](https://garthmortensen.github.io/aca_health/).

## Execution

### create health insurance seed data

- Generate seed data:
  - members
  - plans
  - providers
  - claims and enrollments

`python ./scripts/generate_seed_data.py`

### create database and read seeds

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

## transform

Use dbt to perform all transformations including stage, star-schema analytics mart, summary tables, data cubes and semantic layer.

Install dbt package dependencies:

```bash
dbt deps
```

Run snapshots (captures SCD2 changes for members / plans / providers):

```bash
dbt snapshot
```

Build everything (models + tests).

```bash
dbt build
# or separate:
dbt run
dbt test
```

Gen docs:

```bash
dbt docs generate
dbt docs serve  # opens a local web server
```

Produce single-file static docs for GitHub Pages

```bash
python make_static_docs.py
```

Select executions:

```bash
dbt run --select staging

dbt run --select mart
```

`dbt build` is the one command to materialize all layers + tests.

## Tools

- Containerization: Docker + docker-compose
- Packaging: uv
- Transform modeling: dbt
- Data QA: dbt_expectations (Great Expectations)
- data creation: faker
- linting: Ruff, SQLFluff

## ERDs

## Staging Schema

```mermaid
erDiagram
    staging.claims_raw ||--o{ staging.members_raw : "member_id"
    staging.claims_raw }o--|| staging.providers_raw : "provider_id"
    staging.claims_raw }o--|| staging.plans_raw : "plan_id"
    staging.enrollments_raw ||--|| staging.members_raw : "member_id"
    staging.enrollments_raw }o--|| staging.plans_raw : "plan_id"
```

- Cardinality marks: `||` (one), `o{` (many optional).

## Mart Schema (curated dims & facts)

```mermaid
erDiagram
    mart.dim_member ||--o{ mart.fct_claim : "member_id"
    mart.dim_provider ||--o{ mart.fct_claim : "provider_id"
    mart.dim_plan ||--o{ mart.fct_claim : "plan_id"
    mart.dim_member ||--o{ mart.fct_enrollment : "member_id"
    mart.dim_plan ||--o{ mart.fct_enrollment : "plan_id"
    mart.dim_date ||--o{ mart.fct_claim : "claim_date = full_date"
    mart.dim_date ||--o{ mart.fct_enrollment : "start_date >= full_date <= end_date" 
```

## Summary Schema

```mermaid
erDiagram
    mart.fct_claim ||--o{ summary.agg_claims_monthly : "source"
    mart.fct_claim ||--o{ summary.agg_plan_performance_cube : "source"
    mart.fct_claim ||--o{ summary.agg_provider_specialty_monthly_cube : "source"
    mart.fct_claim ||--o{ summary.agg_claims_diagnosis_summary_cube : "source"
    mart.fct_enrollment ||--o{ summary.agg_plan_performance_cube : "enrollment context"
    mart.dim_member ||--o{ summary.agg_member_cost_cube : "member attributes"
    summary.agg_member_cost_cube ||--o{ summary.agg_member_risk_stratification_cube : "derived"
    summary.agg_claims_monthly ||--|| summary.dashboard_summary : "metrics feed"
    summary.agg_member_cost_cube ||--|| summary.dashboard_summary : "metrics feed"
    summary.agg_provider_performance ||--|| summary.dashboard_summary : "metrics feed"
    summary.agg_provider_performance ||--o{ summary.agg_provider_specialty_monthly_cube : "roll-up"
```

- `source` edges indicate aggregation lineage.
- `metrics feed` indicates inputs to composite dashboard view.
- `derived` indicates a second-level cube built from a first-level cube.

## Semantic Layer

```mermaid
erDiagram
    semantic.metric_definitions ||..|| mart.fct_claim : "references"
    semantic.metric_definitions ||..|| mart.fct_enrollment : "references"
    semantic.time_spine ||--o{ mart.fct_claim : "time grain"
```
