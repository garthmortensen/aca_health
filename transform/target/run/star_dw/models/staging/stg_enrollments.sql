
  create view "dw"."dw"."stg_enrollments__dbt_tmp"
    
    
  as (
    

-- Staging: enrollments (add coverage_days for convenience)
with src as (
  select * from "dw"."staging"."enrollments_raw"
)
select
  enrollment_id,
  member_id,
  plan_id,
  start_date,
  end_date,
  (end_date - start_date + 1)::int as coverage_days,
  premium_paid,
  csr_variant,
  load_id,
  load_timestamp
from src
  );