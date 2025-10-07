# Trend Analysis Data Cubes

## Overview

The trend analysis cubes are pre-aggregated data models designed for efficient year-over-year comparison (2024 vs 2025) of healthcare claims and member metrics. These cubes follow the design pattern from the `Trend_Composition_Agent.ipynb` notebook.

## Models

### 1. `agg_trend_descriptor` (Descriptor Cube)

**Location:** `dw.agg_trend_descriptor`

Contains **claim-level dimensions** with pre-aggregated metrics. This cube provides detailed breakdowns of claims data.

**Key Dimensions:**
- `year` - Calendar year (2024 or 2025)
- `geographic_reporting` - Oscar reporting market (e.g., "OHB (Columbus)", "TX-HN", state codes)
- `claim_type` - Facility, Professional, or RX
- `major_service_category` - HCG service category
- `provider_specialty` - Provider specialty (or "Pharmacy" for RX)
- `channel` - Place of service (IP, OP, SNF, URG, etc.)
- Member demographics: `age_group`, `gender`, `region`, `clinical_segment`
- Member attributes: `plan_metal`, `high_cost_member`, `mutually_exclusive_hcc_condition`

**Key Metrics:**
- `allowed` - Total allowed amount (use for PMPM calculations)
- `charges` - Total charges for paid claims
- `denied_charges` - Total charges for denied claims
- `utilization` - Total utilization count
- `count_of_claims` - Distinct claim count
- `avg_days_service_to_paid` - Average payment turnaround time

### 2. `agg_trend_normalizer` (Normalization Cube)

**Location:** `dw.agg_trend_normalizer`

Contains **member-level dimensions** with enrollment metrics. This cube provides the denominator for normalized calculations.

**Key Dimensions:**
- `year` - Calendar year (2024 or 2025)
- `geographic_reporting` - Same as descriptor cube for joining
- Member demographics: `age_group`, `gender`, `region`, `clinical_segment`
- Member attributes: `plan_metal`, `enrollment_length_continuous`, `new_member_in_period`
- Member engagement: `member_called_oscar`, `member_used_app`, `member_had_web_login`

**Key Metrics:**
- `member_months` - Risk-adjusted member months (denominator for PMPM)
- `unique_members_enrolled` - Count of distinct members

## Usage Examples

### Example 1: Calculate PMPM by Year and Geographic Market

```sql
SELECT 
    d.year,
    d.geographic_reporting,
    ROUND(SUM(d.allowed) / SUM(n.member_months), 2) as pmpm_allowed,
    SUM(d.count_of_claims) as total_claims,
    SUM(n.unique_members_enrolled) as total_members
FROM dw.agg_trend_descriptor d
JOIN dw.agg_trend_normalizer n 
    ON d.year = n.year 
    AND d.geographic_reporting = n.geographic_reporting
    AND d.age_group = n.age_group
    AND d.gender = n.gender
GROUP BY d.year, d.geographic_reporting
ORDER BY d.year, d.geographic_reporting;
```

### Example 2: Year-over-Year Trend by Claim Type

```sql
WITH yearly_metrics AS (
    SELECT 
        d.year,
        d.claim_type,
        SUM(d.allowed) as total_allowed,
        SUM(d.utilization) as total_util,
        SUM(n.member_months) as member_months
    FROM dw.agg_trend_descriptor d
    JOIN dw.agg_trend_normalizer n 
        ON d.year = n.year 
        AND d.geographic_reporting = n.geographic_reporting
        AND d.age_group = n.age_group
    GROUP BY d.year, d.claim_type
)
SELECT 
    claim_type,
    MAX(CASE WHEN year = 2024 THEN ROUND(total_allowed / member_months, 2) END) as pmpm_2024,
    MAX(CASE WHEN year = 2025 THEN ROUND(total_allowed / member_months, 2) END) as pmpm_2025,
    ROUND(
        (MAX(CASE WHEN year = 2025 THEN total_allowed / member_months END) - 
         MAX(CASE WHEN year = 2024 THEN total_allowed / member_months END)) /
        NULLIF(MAX(CASE WHEN year = 2024 THEN total_allowed / member_months END), 0) * 100,
        2
    ) as yoy_change_pct
FROM yearly_metrics
GROUP BY claim_type
ORDER BY claim_type;
```

### Example 3: High-Cost Member Analysis

```sql
SELECT 
    d.year,
    d.high_cost_member,
    COUNT(DISTINCT n.unique_members_enrolled) as member_count,
    SUM(d.allowed) as total_allowed,
    SUM(n.member_months) as member_months,
    ROUND(SUM(d.allowed) / SUM(n.member_months), 2) as pmpm
FROM dw.agg_trend_descriptor d
JOIN dw.agg_trend_normalizer n 
    ON d.year = n.year 
    AND d.high_cost_member = n.high_cost_member
    AND d.age_group = n.age_group
GROUP BY d.year, d.high_cost_member
ORDER BY d.year, d.high_cost_member;
```

### Example 4: Clinical Segment Breakdown

```sql
SELECT 
    d.year,
    d.clinical_segment,
    d.major_service_category,
    SUM(d.allowed) as total_allowed,
    SUM(d.utilization) as total_utilization,
    SUM(n.member_months) as member_months,
    ROUND(SUM(d.allowed) / SUM(n.member_months), 2) as pmpm_allowed
FROM dw.agg_trend_descriptor d
JOIN dw.agg_trend_normalizer n 
    ON d.year = n.year 
    AND d.clinical_segment = n.clinical_segment
    AND d.age_group = n.age_group
    AND d.gender = n.gender
GROUP BY d.year, d.clinical_segment, d.major_service_category
ORDER BY d.year, d.clinical_segment, pmpm_allowed DESC;
```

## Join Keys

When joining the two cubes, use **common dimensions** to ensure proper alignment:

**Recommended join keys:**

- `year` (always required)
- `geographic_reporting`
- `age_group`
- `gender`
- `region`
- `clinical_segment`
- `plan_metal`
- Behavioral flags: `high_cost_member`, `new_member_in_period`, etc.


## Best Practices

1. **Always join on year** - The cubes are designed for year-over-year comparison
2. **Use member_months as denominator** - For all PMPM calculations
3. **Join on appropriate dimensions** - Match the level of aggregation you need
4. **Consider data grain** - Both cubes are pre-aggregated, avoid double-counting
5. **Filter early** - Apply WHERE clauses before joining for better performance

## Rebuild Instructions

```bash
# Regenerate seed data (if needed)
cd /home/garth/projects/aca_health
uv run python scripts/generate_seed_data.py

# Load seeds into database
cd transform
dbt seed --full-refresh

# Build all models including trend cubes
dbt run

# Or build just the trend cubes
dbt run --select agg_trend_descriptor agg_trend_normalizer
```

## Data Lineage

**Fat Fact Table Architecture:**

This data warehouse uses a **fat fact table** design where `fct_claim` includes both metrics AND descriptive attributes. This design choice enables:

- ✅ Simpler queries (fewer joins required)
- ✅ Better query performance
- ✅ Direct analysis on fact tables
- ✅ Proper data warehouse layering (staging → mart → cubes)


```text
Source Data → Seeds
    ├── claims.csv → staging.claims_raw → stg_claims
    ├── members.csv → staging.members_raw → stg_members → member_snapshot (SCD2)
    └── providers.csv → staging.providers_raw → stg_providers
         ↓
Data Mart (in dw schema) - FAT TABLES
    ├── fct_claim (with ALL descriptor fields: claim_type, ms_drg, cpt, drug_name, etc.)
    ├── dim_member (with ALL behavioral/enrollment fields: clinical_segment, call_count, etc.)
    └── dim_provider, dim_plan, dim_date
         ↓
Trend Cubes (pre-aggregated analytics)
    ├── agg_trend_descriptor (claim-level metrics from fct_claim)
    └── agg_trend_normalizer (member-level metrics from dim_member)
```

**Key Difference from Traditional Design:**

- Traditional: Thin fact tables with just FKs and metrics, join to dimensions for attributes
- This warehouse: Fat fact tables with commonly-used attributes denormalized for analysis
- Trend cubes are built FROM the mart layer (not staging), following proper DW best practices


## Current Data Coverage

- **Years:** 2024, 2025
- **Claims:** ~5,200 total (2,500-2,600 per year)
- **Members:** 2,000 total (1,000 per year)
- **Plans:** 20 (10 per year)
- **Providers:** 100 (shared across years)

## Notes

- The cubes use **risk-adjusted member months** (ra_mm) for normalization
- Geographic reporting follows Oscar's market definitions
- Clinical segments: Healthy, Chronic, Behavioral, Maternity, Complex
- Claim types: Facility, Professional, RX
