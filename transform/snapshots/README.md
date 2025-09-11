# Snapshots & Slowly Changing Dimensions (SCD) in This Project

This directory implements historical tracking for core dimensions using dbt **snapshots** plus modeling conventions for various SCD types. It merges guidance previously split across `scd_applies.md` and `scd.md`.

## Why Snapshots?

Operational source records overwrite in-place. dbt snapshots capture row versions over time (Type 2 behavior) by comparing selected columns (either per-column or via a hashdiff) and inserting a new version when they change. This enables as‑of analysis and correct historical joins for facts.

## Fact & Dimension Design (Kimball Recap)

- Facts: represent business events at a declared grain (claim, enrollment period, member-month, premium payment).
- Dimensions: descriptive context shared across facts (member, plan, provider, date, geography). Conformed dimensions allow consistent slicing.
- Decide grain first; measures must be additive at that grain.

Starter fact grains (illustrative): claim line, member-month, enrollment episode (accumulating), premium payment.

## SCD Type Cheat Sheet

- Type 0 (immutable): never changes (e.g., date attributes, intrinsic IDs).
- Type 1 (overwrite): corrects or normalizes (email casing) – history lost.
- Type 2 (row versioning): full change history with `valid_from`, `valid_to`, `is_current`.
- Type 3 (previous value columns): keep current + prior single value.
- Type 4 (historical archive table): rarely needed; split current vs archive.
- Type 6 (1+2+3 hybrid): Type 2 rows plus Type 1 overwrites & previous_* columns.

Practical defaults here: members, plans, providers = Type 2 for business‑relevant changing attributes; some low‑value fields treated Type 1 (format fixes); intrinsic keys Type 0.

## Snapshot Mechanics in dbt

Each snapshot file defines:

```yaml
unique_key: <natural key or composite>
strategy: timestamp|check
```

- Timestamp strategy: compares `updated_at` style column; new row when timestamp advances.
- Check strategy: compares listed columns; new row when any differ.
dbt writes `dbt_valid_from` / `dbt_valid_to`; open rows have `dbt_valid_to` null. Downstream dimension views (our mart layer) often select only current rows or re-alias these to `validity_start_ts` / `validity_end_ts`.

## Change Detection (Hashdiff Pattern)

Instead of enumerating many columns in snapshot configs, staging models can compute a normalized hash (trim, lower, coalesce) of tracked attributes. If hash changes → new Type 2 version. This reduces brittle config edits when adding columns.

## As‑Of Joins

When populating a fact, pick the dimension row valid at the fact’s date:

```sql
SELECT m.member_id
FROM {{ ref('dim_member') }} m
WHERE m.member_id = c.member_id
  AND m.validity_start_ts <= c.claim_date
  AND (m.validity_end_ts IS NULL OR c.claim_date < m.validity_end_ts);
```
Always filter to current rows only for “point-in-time now” style marts; include historical rows for retrospective analytics.

## Periodic & Accumulating Snapshots

- Periodic snapshot fact (e.g., monthly enrollment snapshot): one row per entity per period for trending (PMPM, churn).
- Accumulating snapshot (enrollment episode): single row updated as milestones fill (start, termination). Avoid excessive updates; milestones should be sparse.

## Late Arriving & Inferred Members

If a fact arrives before its dimension change/version: optionally create an inferred Type 2 row flagged `is_inferred`; later, expire and replace when full attributes land. Repair scripts can re-key old facts if a historical backdated row is inserted.

## Testing & Data Quality

- Expect exactly one current row per NK (uniqueness of open version).
- Ensure no overlapping validity intervals for same NK.
- Validate hashdiff determinism (same input → same hash) in unit tests.
- Row count deltas monitored per load for anomaly detection.

## Performance Practices

- Index `(natural_key, is_current)` and `(natural_key, validity_start_ts DESC)` for fast as‑of lookups.
- Keep snapshot relation lean: only store tracked columns + hash + audit fields; enrich later in marts.
- Partition very large Type 2 tables by date if volumes justify.

## Choosing the Right Approach

| Need | Technique |
|------|-----------|
| Full history of attribute | Type 2 snapshot |
| Simple correction / no history | Type 1 overwrite in mart view |
| Prior value alongside current | Type 3 (add `previous_` column) |
| High-churn heavy dimension | Consider Type 4 archive split |
| Hybrid (history + prior + overwrite) | Type 6 |

Default path: implement Type 2 via dbt snapshot → expose current row view in mart → semantic layer references that view → summary aggregates use stable surrogate/natural keys.

## Operations Runbook

1. Load staging raw feed.
2. Compute hashdiffs (if used).
3. Run `dbt snapshot` (creates/expires rows).
4. Run `dbt run` to build mart dims (current row selection) and facts (as‑of joins).
5. Run tests (`dbt test`) to catch overlapping or missing current rows.
6. Refresh summary & semantic layers.

## When NOT to Snapshot

- Source already supplies full version history (no need to duplicate).
- Attribute churn is insignificant and never queried historically.
- Data volume so small that simple Type 1 overwrites suffice.

## Future Enhancements

- Add explicit snapshot tests for non-overlap using custom SQL tests.
- Implement metric-level freshness alerts (late dimension change detection).
- Add provider network bridge with effective dating for in-network analytics.

---
Single source for SCD strategy; original separate docs consolidated for easier maintenance.
