# Snapshots & SCD

This folder tracks changes to key dimension tables using dbt snapshots. Snapshots keep history when source data overwrites in place.

## Why use snapshots?

Source data updates in place. Snapshots record each change, so we can see what data looked like at any point in time. This is called SCD Type 2.

## SCD Types (Summary)

- **Type 0:** Never changes (e.g. dates, IDs)
- **Type 1:** Overwrite, no history (e.g. typo fixes)
- **Type 2:** New row for each change, with valid_from/valid_to
- **Type 3:** Keep current and previous value
- **Type 4:** Archive old rows in a separate table
- **Type 6:** Hybrid (Type 1+2+3)

Default: Use Type 2 for members, plans, providers. Use Type 1 for minor fixes. Use Type 0 for IDs.

## How dbt Snapshots Work

Each snapshot defines a unique key and a strategy (timestamp or check). dbt creates a new row when tracked columns change. Open rows have `dbt_valid_to` as null.

## Change Detection

A hash of tracked columns is used to detect changes. If the hash changes, a new row is created.

## As-Of Joins

To join facts to the correct dimension version, use the row where the fact date is between `valid_from` and `valid_to`.

## Snapshot Types

- **Periodic:** One row per entity per period (e.g. monthly snapshot)
- **Accumulating:** One row per entity, updated as milestones happen

## Testing

- Only one current row per key
- No overlapping date ranges

## Performance

- Index by key and current flag for fast lookups
- Only store needed columns in snapshots

## Which Type to Use?

- Need history? Use Type 2
- Just need latest value? Type 1
- Need previous value too? Type 3
