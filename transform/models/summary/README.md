# Summary Layer (Curated Aggregations / Data Cubes)

The summary schema contains pre‑aggregated, presentation‑ready tables ("lightweight data cubes") built from the mart layer for fast dashboard & KPI access. Unlike the semantic layer—which virtualizes metrics at query time—these models materialize commonly requested rollups to reduce compute and simplify BI consumption.

What makes these cube‑like:

- Defined dimensional cuts (e.g. month, member attributes, provider) baked into each table.
- Precomputed measures (totals, averages, ratios) to avoid repeated on‑the‑fly aggregation.
- Denormalized results tuned for slicing & filtering with minimal joins.
- Stable, predictable grain (monthly, per-member, per-provider) enabling cache‑friendly dashboards.
- Governed alignment with underlying mart & semantic definitions (naming & logic reused, not reinvented).

Table purposes:

- `agg_claims_monthly`: month‑level claims & cost KPIs with approval metrics.
- `agg_member_cost`: per‑member utilization & cost stratification (PMPM / risk tiers).
- `agg_provider_performance`: provider productivity, cost efficiency & categorization.
- `dashboard_summary` (view): single‑row KPI snapshot composed from the other aggregates.

Use this layer when: a dashboard hits the same metric set repeatedly, latency matters, or end users shouldn't craft complex joins. If a metric is exploratory or ad‑hoc, prefer querying the semantic layer directly instead of expanding a cube.

Avoid adding: highly sparse high‑dimensional cubes (explosion risk), one‑off analyst questions, or raw granular data (belongs in mart).

Lifecycle tip: start with semantic metrics, promote high‑usage patterns here once stable, and periodically prune stale aggregates.

## How dbt handles this folder

- Schema override: `dbt_project.yml` sets `+schema: summary`, so these relations land in a dedicated database schema separate from raw/mart tables.
- Materializations: Generally `table` for stable aggregates; `dashboard_summary` is a `view` to stay light and reflect upstream changes instantly.
- Dependencies: Each aggregate uses `ref()` to mart layer models; dbt ensures lineage (mart -> summary) and rebuild ordering.
- Rebuild strategy: For time-series additive tables you could convert to `incremental` later—current full rebuild keeps logic simple while data volume is modest.
- Testing: Column tests (ranges, sets) live alongside the models (`schema.yml`) to guard KPI drift or data explosions.
- Use with semantic layer: Semantic metrics can still reference these aggregates if needed, but preferred flow is mart -> semantic (virtual) OR mart -> summary (materialized), not both unless there’s a strong performance case.
- Change management: Adjusting a metric here requires DDL/DML (rebuild); if experimentation is ongoing, define it first virtually in the semantic layer before promoting.
