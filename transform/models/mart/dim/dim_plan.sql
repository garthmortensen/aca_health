{{ config(materialized='view', schema='dw') }}
-- moved from analytics to mart
select
    s.plan_id,
    upper(s.name) as plan_name,
    s.metal_tier,
    s.monthly_premium,
    s.deductible,
    s.oop_max,
    s.coinsurance_rate,
    s.pcp_copay,
    s.effective_year,
    s.dbt_valid_from as validity_start_ts,
    s.dbt_valid_to   as validity_end_ts,
    (s.dbt_valid_to is null) as is_current
from {{ ref('plan_snapshot') }} s
where s.dbt_valid_to is null
