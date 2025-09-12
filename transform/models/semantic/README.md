# Semantic Layer

This folder defines business metrics and entities in a way that makes them easy to use and consistent across all dashboards and tools. It does not contain summary tables—those are in the `summary/` folder.

What this folder does:

- Lists the main business entities (like claim, member, enrollment)
- Defines important numbers (like total claim amount, approval rate, total premium paid)
- Sets up how you can filter and group by things like time or category
- Includes a special table for dates (`time_spine`) to help with time-based analysis
- Does not store pre-calculated data—metrics are calculated when you query them

Key files:

- `semantic_models.yml`: lists entities, dimensions, and measures
- `metrics.yml`: (for future use) will hold more complex metrics
- `_models.yml` and `time_spine.sql`: set up the date table
- `schema.yml`: minimal, since most tests are with the mart tables

Add something here if:

- You want a new metric or relationship to be available everywhere
- You want to avoid repeating metric logic in different dashboards

Don’t add here if:

- You just need a one-off summary table (use `summary/`)
- You are building a table for a specific dashboard (also use `summary/`)

## How dbt uses this folder

- The YAML files here are read by dbt to define metrics and entities, but they do not create tables or views
- Each semantic model points to a real table in the mart layer
- The `time_spine.sql` file creates a date table for time-based analysis
- Most tests are done in the mart layer, not here
