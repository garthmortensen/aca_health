{{ config(materialized='incremental', unique_key='enrollment_id') }}

with enrollments as (
    select * from {{ ref('stg_enrollments') }}
), dim_member as (
    select member_id from {{ ref('dim_member') }}
), dim_plan as (
    select plan_id from {{ ref('dim_plan') }}
)
select
    e.enrollment_id,
    e.member_id,
    e.plan_id,
    e.start_date,
    e.end_date,
    e.coverage_days,
    e.premium_paid,
    e.csr_variant,
    e.load_id,
    e.load_timestamp
from enrollments e
left join dim_member dm using (member_id)
left join dim_plan dp using (plan_id)

{% if is_incremental() %}
where e.load_timestamp > (select coalesce(max(load_timestamp), '1900-01-01') from {{ this }})
{% endif %}
