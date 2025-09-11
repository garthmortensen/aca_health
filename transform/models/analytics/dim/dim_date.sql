{{ config(materialized='table') }}
-- Date dimension generated on the fly (adjust range as needed)
with days as (
  select generate_series(date '2000-01-01', date '2030-12-31', interval '1 day')::date as d
)
select
  extract(year from d)::int * 10000 + extract(month from d)::int * 100 + extract(day from d)::int as date_key,
  d as full_date,
  extract(year from d)::int as year,
  extract(quarter from d)::smallint as quarter,
  extract(month from d)::smallint as month,
  to_char(d,'Mon') as month_name,
  extract(day from d)::smallint as day,
  extract(isodow from d)::smallint as day_of_week,
  to_char(d,'Dy') as day_name,
  extract(week from d)::smallint as week_of_year,
  (extract(isodow from d) in (6,7)) as is_weekend,
  now() as created_at
from days
