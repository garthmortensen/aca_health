{{ config(materialized='table') }}

-- Member cost cube (member x cost metrics)
-- Renamed from agg_member_cost to enforce cube naming convention (multi-dimension)
-- Source: dim_member + fct_claim + fct_enrollment aggregated in prior logic.

-- Reuse original logic from agg_member_cost (kept identical)
with member_enrollment_months as (
    select e.member_id, e.plan_id, sum(e.coverage_days) / 30.44 as total_enrollment_months
    from {{ ref('fct_enrollment') }} e
    where e.start_date >= '2025-01-01'
    group by e.member_id, e.plan_id
),
member_claims_cost as (
    select c.member_id, count(c.claim_id) as total_claims, sum(c.claim_amount) as total_billed, sum(c.allowed_amount) as total_allowed, sum(c.paid_amount) as total_paid
    from {{ ref('fct_claim') }} c
    where c.claim_date >= '2025-01-01'
    group by c.member_id
),
member_demographics as (
    select member_id, age_group, gender, region, plan_metal, is_current
    from {{ ref('dim_member') }}
)
select md.member_id, md.age_group, md.gender, md.region, md.plan_metal,
    coalesce(mem.total_enrollment_months, 0) as enrollment_months,
    coalesce(mcc.total_claims, 0) as total_claims,
    coalesce(mcc.total_billed, 0) as total_billed_amount,
    coalesce(mcc.total_allowed, 0) as total_allowed_amount,
    coalesce(mcc.total_paid, 0) as total_paid_amount,
    case when coalesce(mem.total_enrollment_months, 0) > 0 then coalesce(mcc.total_paid, 0) / mem.total_enrollment_months else 0 end as pmpm_cost,
    case when coalesce(mem.total_enrollment_months, 0) > 0 then (coalesce(mcc.total_paid, 0) / mem.total_enrollment_months) * 12 else 0 end as pmpy_cost,
    case when coalesce(mem.total_enrollment_months, 0) > 0 then coalesce(mcc.total_claims, 0) / mem.total_enrollment_months else 0 end as claims_per_member_per_month,
    case 
        when coalesce(mcc.total_paid, 0) = 0 then 'No Claims'
        when coalesce(mcc.total_paid, 0) <= 500 then 'Low Cost'
        when coalesce(mcc.total_paid, 0) <= 2000 then 'Moderate Cost'
        when coalesce(mcc.total_paid, 0) <= 10000 then 'High Cost'
        else 'Very High Cost'
    end as cost_category
from member_demographics md
left join member_enrollment_months mem on md.member_id = mem.member_id
left join member_claims_cost mcc on md.member_id = mcc.member_id
where md.is_current = true
order by total_paid_amount desc
