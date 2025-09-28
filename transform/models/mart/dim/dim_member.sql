{{ config(materialized='view', schema='dw') }}
-- moved from analytics to mart
select
    s.member_id,
    upper(s.first_name) as first_name,
    upper(s.last_name)  as last_name,
    s.dob as date_of_birth,
    s.gender,
    s.age_group,
    s.region,
    s.plan_metal,
    s.load_id,
    s.dbt_valid_from as validity_start_ts,
    s.dbt_valid_to   as validity_end_ts,
    (s.dbt_valid_to is null) as is_current
from {{ ref('member_snapshot') }} s
where s.dbt_valid_to is null
