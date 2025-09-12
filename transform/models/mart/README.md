# Mart Layer

Facts record business events (like claims or enrollments). Dimensions describe those events (like member, plan, provider, date).

Key points:

- Shared dimensions connect to many facts for consistent analysis
- Each fact table has a clear grain (one row per event)
- Dimensions use snapshots to keep history (SCD2)
- Facts are kept simple: just keys and numbers; details live in dimensions

Why do this?

- Makes joins and analysis consistent
- Reuse measures and logic across reports
- Prevents double counting

Dashboards and heavy aggregations are handled in the `../summary/` folder. 

Semantic definitions are in `../semantic/`.

## How dbt builds these models

- Most dimensions are views; facts are incremental tables
- Naming follows `<schema>.<model_name>`
- Facts use `ref()` to staging; dimensions use `ref()` to snapshots
- Tests for uniqueness and referential integrity are in `schema.yml`
- Full refresh is only needed if history logic changes
- SQL is kept simple for performance and debugging
