# Semantic Layer Models

This folder contains the dbt **semantic layer** definitions that turn raw dimensional & fact models into governed, reusable business metrics. These are *not* the aggregated summary tables (those live in `../summary/`). Instead they define the **semantic contract** that downstream tools (BI, notebooks, APIs) can query consistently.

What makes a model here "semantic":

1. Explicit entity & grain declarations (e.g. claim, member, enrollment) in `semantic_models.yml`.
2. Governed measures (sums, counts, averages, ratios) with business names: `total_claim_amount`, `approval_rate`, `total_premium_paid`, etc.
3. Typed dimensions (time, categorical) enabling consistent filtering & time‑series rollups.
4. A canonical `time_spine` table to standardize date grain alignment for time-based metrics.
5. Separation from physical aggregation: aggregation happens on‑demand via the semantic layer rather than being pre‑materialized here.

Key files:

- `semantic_models.yml` – declares entities, dimensions, measures for claims & enrollments, plus members.
- `metrics.yml` – (placeholder) would house metric definitions composing measures (add as they mature).
- `_models.yml` & `time_spine.sql` – provide the date spine required for time-aware metrics.
- `schema.yml` – kept minimal; tests for the semantic models now live with their underlying mart tables.

When to add something here:

- You need a new governed measure or entity relationship.
- You want a metric available uniformly across dashboards without recreating logic.

When *not* to add it here:

- You just need a one-off summary table (use `summary/`).
- You’re building a presentation-ready aggregation (also `summary/`).

Next ideas: flesh out `metrics.yml` with composed metrics (e.g. cost PMPM), add semantic coverage for providers, and implement metric tests via dbt-expectations.

## How dbt handles this folder

- Compilation only references: `semantic_models.yml` and `metrics.yml` are parsed (not executed) and merged into the manifest; they don't produce relations.
- Dependency resolution: Each semantic model points to a physical mart model via `model: ref('...')`; dbt ensures the underlying table/view builds first.
- Time spine: `time_spine.sql` builds a physical table; the `_models.yml` entry attaches metadata (granularity) consumed by the semantic layer.
- Testing: Column & relationship tests live with source mart models; semantic definitions inherit consistency by referencing those tested relations.
- Environments: The configured target schema (plus custom schemas) still applies; semantic YAML does not change database naming, only exposes metadata for downstream metric serving.
- Extensibility: Add new measures without altering consuming dashboards—dbt recompiles the manifest and the semantic service exposes the new metric instantly.
