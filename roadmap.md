# Roadmap (Simple)

## COMPLETE

1. Generate synthetic ACA CSV source files (Extract step ready).
2. Create Postgres staging schema and raw tables plus load_batches audit table.
3. Implement idempotent staging loader to ingest newest CSVs.
4. Load initial raw data into staging tables
   - Run:`python -m etl.load.staging_loader`.
5. Finish minor loader hardening (optional: checksum, validation queries).
   - Add columns to load_batches: file_size_bytes, file_sha256, source_row_count (to detect altered same-name files).

## TODO

6. Create core dimension tables (DimDate, DimMember, DimPlan, DimProvider) with SCD2 columns.
7. Populate DimDate and build SCD2 upsert (hash change detection) for other dimensions.
8. Create fact tables (FactClaim, FactEnrollment) and load via surrogate key resolution.
9. Add data quality checks (row counts, PK/FK, nulls, duplicates) and orchestration script.
10. Build summary views (claims by metal tier, member utilization) to validate analytics layer.
