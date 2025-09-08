# Infrastructure Database Structure

This directory contains the organized database schema, procedures, and migration files for the Star (schema) data warehouse project.

This project now uses dbt as the primary transformation tool. The SQL files in this directory provide the foundational schema, while dbt models handle the ETL transformations.

## Directory Structure

```text
infrastructure/database/
├── schemas/         # Base table definitions (DDL)
├── procedures/      # Legacy ETL procedures (now replaced by dbt)
├── migrations/      # Schema change tracking
└── README.md
```

## Current Architecture

### Primary ETL via dbt

The transformation pipeline:

- **Staging Layer**: `transform/models/staging/` - Clean and standardize raw data
- **Snapshots**: `transform/snapshots/` - SCD2 historical tracking for dimensions
- **Analytics Layer**: `transform/models/analytics/` - Star schema dimensions and facts
- **Semantic Layer**: `transform/models/semantic/` - Business metrics and KPIs

### Database Schema Foundation

The SQL schemas provide the foundational structure:

- **01_staging.sql** - Raw data staging tables (claims_raw, enrollments_raw, etc.)
- **02_comments.sql** - Column comment definitions for data dictionary  
- **03_warehouse.sql** - Target dimensional model structure

### Legacy Procedures

The procedures directory contains the original SQL ETL logic, now replaced by dbt models:

- **01_load_dim_date.sql** - Calendar population (now handled by `dim_date.sql` model)
- **02_load_dimensions.sql** - SCD2 loading (now handled by dbt snapshots)  
- **03_load_facts.sql** - Fact loading (now handled by incremental fact models)

## Schema Execution Order

For a fresh database setup, run schemas in this order:

1. `01_staging.sql` - Creates staging schema and raw tables
2. `02_comments.sql` - Adds column documentation
3. `03_warehouse.sql` - Creates dimensional warehouse (dw) schema

Then run procedures in order:

1. `01_load_dim_date.sql` - Populate date dimension first
2. `02_load_dimensions.sql` - Load member/provider/plan dimensions (with SCD2)
3. `03_load_facts.sql` - Load fact tables (requires dimensions to exist)

## Key Features

### Staging Layer

- Raw CSV data ingestion tables
- Minimal constraints for flexibility
- Load batch tracking with `load_batches` table
- Timestamp-based idempotency support

### Warehouse Layer

- **Dimensional Model**: Star schema with dimensions and facts
- **SCD Type 2**: Full history tracking for member, provider, and plan changes
- **Surrogate Keys**: Auto-incrementing surrogate keys for all dimensions
- **Date Dimension**: Pre-populated calendar table with business attributes
- **Fact Tables**: Claims and enrollment facts with proper foreign key relationships

### Data Quality

- Referential integrity enforced via foreign keys
- Unique constraints on natural keys + validity dates
- NOT NULL constraints on critical fields
- Indexes optimized for typical query patterns

## Usage with dbt

This schema structure supports the dbt models in `transform/models/`:

- **Staging models** (`stg_*`) read from staging schema
- **Dimension models** (`dim_*`) populate warehouse dimensions
- **Fact models** (`fct_*`) populate warehouse facts
- **Semantic models** use warehouse tables for MetricFlow
