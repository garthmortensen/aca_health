# Trend Analysis Data Cubes

## Overview

{% docs trend_cubes_overview %}
The trend analysis cubes are **pre-aggregated analytical tables** designed for efficient year-over-year healthcare cost and utilization analysis. These cubes follow dimensional modeling best practices and enable rapid calculation of:

- PMPM (Per Member Per Month) metrics
- Year-over-year trend analysis (2024 vs 2025)
- Cost and utilization breakdowns by provider, service, and member demographics
- Geographic market comparisons

## Architecture

These cubes use a **fat fact table design** where:

- Facts include both metrics AND commonly-used dimensional attributes
- This design reduces join complexity and improves query performance
- Data flows: Seeds → Staging → Mart (Fat Facts) → Trend Cubes

## Usage Pattern

Example PMPM calculation by joining descriptor and norm cubes:

```sql
SELECT
    d.year,
    d.claim_type,
    SUM(d.allowed) / SUM(n.member_months) AS pmpm_allowed
FROM agg_trend_descriptor d
JOIN agg_trend_normalizer n
    ON d.year = n.year
    AND d.geographic_reporting = n.geographic_reporting
    AND d.age_group = n.age_group
    AND d.gender = n.gender
GROUP BY d.year, d.claim_type;
```
{% enddocs %}

{% docs trend_descriptor_definition %}
**Descriptor Cube** contains claim-level data with pre-aggregated metrics. Use this cube for:

- Claim cost analysis by service type, provider, procedure code
- Utilization metrics and denial rate tracking
- Payment turnaround time analysis

**Grain:** One row per unique combination of claim dimensions (year, geography, service category, provider specialty, member demographics, etc.)
{% enddocs %}

{% docs trend_norm_definition %}
**Normalization Cube** contains member-level enrollment data. Use this cube for:

- Calculating denominators for PMPM metrics
- Member cohort analysis
- Enrollment and engagement tracking

**Grain:** One row per unique combination of member dimensions (year, geography, demographics, clinical segment, etc.)

**Key Metric:** `member_months` - Risk-adjusted member months used as the denominator for all PMPM calculations
{% enddocs %}

{% docs geographic_reporting_logic %}
Oscar's market reporting logic:

- **OHB (Columbus)**: HIOS IDs starting with 29341
- **OHC (Cleveland Clinic Product)**: HIOS IDs starting with 45845
- **TX-HN, TX-PPO**: Texas broken out by network type
- **Other states**: Reported at state level

This field enables consistent market-level reporting across the organization.
{% enddocs %}

{% docs clinical_segment_values %}
Member clinical complexity segments:

- **Healthy**: No chronic conditions, minimal utilization
- **Chronic**: Stable chronic conditions (diabetes, hypertension, asthma)
- **Behavioral**: Mental health or substance use conditions
- **Maternity**: Pregnant members or recent deliveries
- **Complex**: Multiple chronic conditions, high utilization, or serious diagnoses

Used for risk stratification and targeted interventions.
{% enddocs %}

{% docs member_months_metric %}
**Risk-Adjusted Member Months (ra_mm)**

The primary denominator for PMPM calculations. Calculated as:

```sql
base_mm = enrollment_length_continuous / 12
ra_mm = base_mm × risk_multiplier
```

Risk multipliers based on:

- Clinical segment (Complex: 1.8x, Chronic: 1.4x, Behavioral: 1.3x, Maternity: 1.2x)
- Age (65+: 1.2x, 55-64: 1.1x)
- HCC conditions (+15%)
- High-cost flag (+50%)

This ensures proper normalization accounting for member risk profiles.
{% enddocs %}

{% docs pmpm_calculation_pattern %}
**Standard PMPM Calculation Pattern:**

Example of joining descriptor and norm cubes:

```sql
-- Always join on common dimensions
SELECT
    d.year,
    d.geographic_reporting,
    SUM(d.allowed) AS total_allowed,
    SUM(n.member_months) AS member_months,
    SUM(d.allowed) / NULLIF(SUM(n.member_months), 0) AS pmpm_allowed
FROM agg_trend_descriptor d
JOIN agg_trend_normalizer n
    ON d.year = n.year
    AND d.geographic_reporting = n.geographic_reporting
    AND d.age_group = n.age_group
    AND d.gender = n.gender
    -- Add other common dimensions as needed
GROUP BY d.year, d.geographic_reporting;
```

**Key Points:**

1. Always join on year + common dimensions
2. Use member_months from norm cube as denominator
3. Use NULLIF to avoid division by zero
4. Round results appropriately for display
{% enddocs %}
