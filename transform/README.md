# dbt Transformations & Datacube

This directory contains all dbt transformations that build the star schema data warehouse and semantic datacube layer.

## Architecture Overview

```text
Raw CSV Data → Staging → Snapshots → Analytics → Semantic (Datacube)
     ↓            ↓          ↓           ↓            ↓
   Source      Clean      SCD2      Star Schema   Business Ready
   Files       Data     History    Dim/Facts      Aggregations
```

## Datacube Components

The **Semantic Layer** (`models/semantic/`) contains our datacube implementations:

### Current Datacube Models

1. **`agg_claims_monthly`** - Monthly Claims Cube
   - **Dimensions**: Time (monthly), claim status, member segments
   - **Measures**: Claims volume, costs, approval rates, unique members/providers
   - **Business Use**: Monthly reporting, trend analysis

2. **`agg_member_cost`** - Member Cost Analysis Cube  
   - **Dimensions**: Member demographics, cost categories, time
   - **Measures**: PMPM/PMPY costs, utilization rates, risk segmentation
   - **Business Use**: Member risk stratification, cost management

3. **`agg_provider_performance`** - Provider Performance Cube
   - **Dimensions**: Provider specialty, geography, volume categories
   - **Measures**: Claims volume, approval rates, cost efficiency metrics
   - **Business Use**: Network management, provider scorecards

4. **`dashboard_summary`** - Executive KPI Cube
   - **Dimensions**: Aggregated across all domains
   - **Measures**: High-level KPIs, cost concentration, network metrics
   - **Business Use**: C-suite dashboards, executive reporting

## What Makes These "Datacubes"

These models qualify as datacubes because they provide:

1. **Multi-dimensional Analysis** - Time, member segments, plan types, provider specialties
2. **Pre-aggregated Measures** - Claims volume, costs, approval rates, PMPM/PMPY
3. **OLAP-style Queries** - Slice/dice across dimensions for BI dashboards
4. **Star Schema Foundation** - Built on Kimball dimensional model

## Data Flow

### Analytics Layer (`models/analytics/`)

- **Purpose**: Star schema dimensional model
- **Dimensions**: `dim_date`, `dim_member`, `dim_plan`, `dim_provider`
- **Facts**: `fct_claim`, `fct_enrollment`
- **Approach**: Current records from snapshots + incremental facts

### Semantic/Datacube Layer (`models/semantic/`)

- **Purpose**: Business-ready aggregations and metrics
- **Strategy**: Pre-calculated cubes for fast BI queries
- **Materialization**: Tables for performance

## Business Value

**Quick Summary**: A datacube requires pre-aggregated measures across multiple dimensions for OLAP analysis. The lower layers (staging, dimensions, facts) store atomic data but don't provide the aggregated, multi-dimensional views needed for business intelligence.

### What's NOT the Datacube

- **Raw staging tables** - Data storage layer (1:1 with source, no aggregation)
- **Dimensional tables** - Building blocks for cubes (descriptive attributes, not measures)
- **Fact tables** - Atomic data, not aggregated (individual claims/enrollments, not summarized)

### What IS the Datacube

- **Semantic layer models** - Pre-aggregated business metrics
- **Multi-dimensional analysis** - Slice/dice capabilities
- **Performance-optimized** - Fast queries for dashboards
- **Business-aligned** - Metrics that matter to stakeholders

The semantic layer essentially creates a datacube that sits on top of the star schema foundation, providing fast, business-ready analytics for healthcare insurance operations.
