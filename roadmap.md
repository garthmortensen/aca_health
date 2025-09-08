# Roadmap (Simple)

## COMPLETE ✅

1. Generate synthetic ACA CSV source files (Extract step ready).
   - Run `python ./scripts/generate_seed_data.py`
   - Use timestamp as seed (seed embedded in filename)

2. Create Postgres staging schema and raw tables plus load_batches audit table.
   - Kill all data `docker compose -f infrastructure/docker/docker-compose.yml down -v`
   - Build `docker compose -f infrastructure/docker/docker-compose.yml up -d`

3. Implement idempotent staging loader to ingest newest CSVs and load raw data into staging.
   - Run: `python scripts/staging_loader.py`
   - Using .loaded_filenames with filename-based tracking
   - ✅ FIXED: First row issue (removed duplicate header handling)

4. Create core dimension tables (DimDate, DimMember, DimPlan, DimProvider) with SCD2 columns.
   - ✅ Implemented via dbt snapshots and dimension models

5. Create fact tables (FactClaim, FactEnrollment).
   - ✅ Implemented via dbt incremental models

6. Implement a semantic layer called semantic
   - ✅ agg_claims_monthly, agg_member_cost, agg_provider_performance, dashboard_summary

7. Infrastructure reorganization (sql/ddl,etl → database/schemas,procedures structure)
   - ✅ Completed directory reorganization with migration tracking

8. **dbt Integration Complete**:
   - ✅ Staging models (`stg_*`) for clean data transformation
   - ✅ Snapshots for SCD2 historical tracking
   - ✅ Dimension models (`dim_*`) with current records
   - ✅ Fact models (`fct_*`) with incremental loading
   - ✅ Semantic layer with business metrics and KPIs
   - ✅ Data quality tests for all models

**Current workflow:** `cd transform && dbt run && dbt test`

## TODO

1. **Enhanced Data Quality** (optional):
   - Add custom dbt tests for business rules
   - Implement Great Expectations integration
   - Add row count reconciliation tests

2. **Semantic Layer Expansion** (optional):
   - Add MetricFlow configuration for dbt Semantic Layer
   - Create additional metrics for provider network analysis
   - Add time-based analysis (seasonality, trending)

3. **Sandbox Environment** (planned):
   - Implement a scratchpad schema called sandbox
   - Add to dbt run when created

4. **Advanced Analytics** (future):
   - Risk stratification models
   - Provider recommendation engine
   - Claims anomaly detection

5. **Performance Optimization** (future):
   - Implement incremental snapshots
   - Add partitioning for large fact tables
   - Optimize query performance for dashboard models
