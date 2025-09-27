{{ config(materialized='view') }}

-- Staging: enrollments (add coverage_days for convenience)
with latest as (
  select max(load_id) as load_id from {{ source('staging','enrollments_raw') }}
), src as (
  select * from {{ source('staging','enrollments_raw') }} where load_id = (select load_id from latest)
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
