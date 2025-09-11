{{ config(materialized='table') }}

-- Time spine model required for dbt semantic layer
-- This provides a continuous date series for time-based analysis

select
    full_date as date_day
from {{ ref('dim_date') }}
where full_date >= '2020-01-01'
  and full_date <= '2030-12-31'
