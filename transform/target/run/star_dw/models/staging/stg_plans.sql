
  create view "dw"."dw"."stg_plans__dbt_tmp"
    
    
  as (
    

-- Staging: plans (clean + light typing / renames if needed)
with src as (
  select * from "dw"."staging"."plans_raw"
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
  );