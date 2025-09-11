# Mart Layer (Kimball Dimensions & Facts)

This folder holds the conformed dimensional model of the warehouse following classic Kimball principles: clear business process facts joined to shared dimensions via surrogate keys. These models are the semantic foundation that the dbt Semantic Layer and downstream marts/aggregations build on.

Core ideas applied here:

- Bus Architecture: shared dimensions (`dim_member`, `dim_plan`, `dim_provider`, `dim_date`) act as conformed hubs for multiple facts.
- Grain First: each fact (`fct_claim`, `fct_enrollment`) declares a single, atomic grain (one row per claim / per enrollment period) enabling additive measures.
- Surrogate Keys & SCD2: dimensions are sourced from snapshots (SCD2) preserving history while exposing a current row flag for convenience.
- Thin Facts, Rich Dimensions: facts store foreign keys + numeric measures; descriptive attributes live in dimensions for reuse and consistency.
- Incremental Loading: large facts are incremental to keep builds fast while dimensions (except `dim_date`) are views over current snapshot rows.

Why this matters:

- Consistent joins & drill paths across analytics artifacts.
- Reusable measures (e.g. total_claim_amount, premium_paid) flow into semantic metrics and summary cubes without redefining logic.
- Stable grain prevents double counting and supports time-series rollups.

Add a new dimension when you introduce a new descriptive entity reused by multiple facts. Add a fact when you model a new business event/process with measurable KPIs.

Out of scope here: heavy aggregation for dashboards (use `../summary/`), semantic entity/measure declarations (`../semantic/`).

## How dbt handles this folder

- Folder config: `dbt_project.yml` maps `models/mart` to the project, applying default `+materialized: view` (overridden per model where needed: incremental/table).
- Materializations: Dimensions are usually `view` (fast rebuild) except static helpers (e.g. `dim_date` as a `table`). Facts use `incremental` with a `unique_key` to support efficient appends.
- Naming: Final relation names follow target naming (`<schema>.<model_name>`); surrogate keys / natural keys are not auto-generated—logic lives in snapshots & staging.
- Lineage: Facts `ref()` their staging sources; dimensions `ref()` snapshot objects, enabling dbt to order builds and show lineage graphs.
- Tests: Uniqueness & referential integrity defined in `schema.yml` (now relocated here) run after build; failures block deploys.
- Deployment: Full refresh only needed when historical logic changes (e.g. re-computing grains). Incremental runs default to processing new loads based on `load_timestamp` fields.
- Performance: Pushing filters/joins to warehouse; minimal Jinja logic keeps SQL readable and debuggable.
