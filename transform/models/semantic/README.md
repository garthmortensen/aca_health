
# Semantic Layer


This folder defines business metrics and entities in a way that makes them easy to use and consistent across all dashboards and tools. It does not contain summary tables—those are in the `summary/` folder.

## Use Case

The semantic layer acts as a translation layer between your raw data and business users or analytics tools. It enables:

- Consistent, reusable business metrics across all dashboards and tools
- Self-service analytics for business users (no SQL required)
- Centralized logic for metrics and dimensions, reducing errors and duplication
- Integration with BI tools and APIs for easy metric exploration

You cannot query the semantic layer directly with SQL (e.g., `SELECT * FROM table`). Instead, you use compatible tools or APIs to access the metrics and entities defined here.

What this folder does:

- Lists the main business entities (like claim, member, enrollment)
- Defines important numbers (like total claim amount, approval rate, total premium paid)
- Sets up how you can filter and group by things like time or category
- Includes a special table for dates (`time_spine`) to help with time-based analysis
- Does not store pre-calculated data—metrics are calculated when you query them

## Key files:

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

## How to Use the Semantic Layer

- **dbt Semantic Layer Tool:**
	- Use the [dbt Semantic Layer](https://docs.getdbt.com/docs/semantic-layer/overview) (available via API) to serve and query metrics defined in this folder.
	- Connect compatible BI tools (e.g., Hex, Mode, Lightdash) or use the dbt Semantic Layer API to explore and query metrics.

## How dbt uses this folder

- The YAML files here are read by dbt to define metrics and entities, but they do not create tables or views
- Each semantic model points to a real table in the mart layer
- The `time_spine.sql` file creates a date table for time-based analysis
- Most tests are done in the mart layer, not here

## API Access

You can access and query metrics programmatically using the dbt Semantic Layer API. See the [dbt docs](https://docs.getdbt.com/docs/semantic-layer/overview) for more details.
