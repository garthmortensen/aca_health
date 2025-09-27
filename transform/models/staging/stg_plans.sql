{{ config(materialized='view') }}

-- Staging: plans (clean + light typing / renames if needed)
with latest as (
  select max(load_id) as load_id from {{ source('staging','plans_raw') }}
), src as (
  select * from {{ source('staging','plans_raw') }} where load_id = (select load_id from latest)
)
select
  plan_id,
  name as plan_name,
  metal_tier,
  monthly_premium::numeric(10,2) as monthly_premium,
  deductible,
  oop_max,
  coinsurance_rate,
  pcp_copay,
  effective_year,
  load_id,
  load_timestamp
from src
