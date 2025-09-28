{{ config(materialized='table', schema='summary') }}

-- Diagnosis cube (diagnosis x month) top 50 per month
with diagnosis_monthly as (
    select date_trunc('month', c.claim_date) as report_month,
           c.diagnosis_code,
           count(c.claim_id) as total_claims,
           sum(c.claim_amount) as total_billed_amount,
           sum(c.allowed_amount) as total_allowed_amount,
           sum(c.paid_amount) as total_paid_amount,
           count(distinct c.member_id) as unique_members,
           count(distinct c.provider_id) as unique_providers,
           row_number() over (partition by date_trunc('month', c.claim_date) order by count(c.claim_id) desc) as rn
    from {{ ref('fct_claim') }} c
    where c.claim_date >= '2025-01-01'
    group by 1,2
)
select report_month,
       diagnosis_code,
       total_claims,
       unique_members,
       unique_providers,
       total_billed_amount,
       total_allowed_amount,
       total_paid_amount,
       case when total_billed_amount>0 then total_allowed_amount/total_billed_amount else 0 end as allowance_ratio,
       case when total_allowed_amount>0 then total_paid_amount/total_allowed_amount else 0 end as payment_ratio
from diagnosis_monthly
where rn <= 50
order by report_month, total_claims desc
