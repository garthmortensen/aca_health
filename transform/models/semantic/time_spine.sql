{{ config(
    materialized='table'
) }}

-- Time spine model for dbt semantic layer
-- Must be named exactly 'time_spine' and have column 'date_day'

with spine as (
    select 
        generate_series(
            '2020-01-01'::date,
            '2030-12-31'::date,
            '1 day'::interval
        )::date as date_day
)

select 
    date_day
from spine
order by date_day
