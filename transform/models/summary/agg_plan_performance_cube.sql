{{ config(materialized='table') }}

-- Plan performance cube (plan x month)
with plan_claims as (
    select p.plan_id,
           date_trunc('month', c.claim_date) as report_month,
           count(c.claim_id) as total_claims,
           sum(c.claim_amount) as total_billed_amount,
           sum(c.allowed_amount) as total_allowed_amount,
           sum(c.paid_amount) as total_paid_amount,
           count(distinct c.member_id) as unique_members_with_claims,
           sum(case when c.claim_status = 'approved' then 1 else 0 end) as approved_claims,
           sum(case when c.claim_status = 'denied' then 1 else 0 end) as denied_claims
    from {{ ref('fct_claim') }} c
    join {{ ref('dim_plan') }} p on c.plan_id = p.plan_id
    where c.claim_date >= '2025-01-01'
    group by 1,2
),
plan_enrollment as (
    select e.plan_id,
           date_trunc('month', e.start_date) as report_month,
           sum(e.coverage_days)/30.44 as member_months
    from {{ ref('fct_enrollment') }} e
    where e.start_date >= '2025-01-01'
    group by 1,2
)
select pc.plan_id,
       pc.report_month,
       pc.total_claims,
       pc.total_billed_amount,
       pc.total_allowed_amount,
       pc.total_paid_amount,
       pc.unique_members_with_claims,
       coalesce(pe.member_months,0) as member_months,
       case when pc.total_billed_amount>0 then pc.total_allowed_amount/pc.total_billed_amount else 0 end as allowance_ratio,
       case when pc.total_allowed_amount>0 then pc.total_paid_amount/pc.total_allowed_amount else 0 end as payment_ratio,
       case when coalesce(pe.member_months,0)>0 then pc.total_paid_amount / pe.member_months else 0 end as pmpm_paid,
       case when pc.total_claims>0 then pc.approved_claims::float/pc.total_claims else 0 end as approval_rate,
       pc.denied_claims
from plan_claims pc
left join plan_enrollment pe using(plan_id, report_month)
order by report_month, plan_id
