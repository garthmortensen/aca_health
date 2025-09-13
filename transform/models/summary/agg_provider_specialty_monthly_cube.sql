{{ config(materialized='table') }}

-- Provider specialty performance cube (specialty x month)
with claims as (
    select p.specialty,
           date_trunc('month', c.claim_date) as report_month,
           count(c.claim_id) as total_claims,
           sum(c.claim_amount) as total_billed_amount,
           sum(c.allowed_amount) as total_allowed_amount,
           sum(c.paid_amount) as total_paid_amount,
           sum(case when c.claim_status='approved' then 1 else 0 end) as approved_claims,
           sum(case when c.claim_status='denied' then 1 else 0 end) as denied_claims,
           count(distinct c.member_id) as unique_members,
           count(distinct c.provider_id) as unique_providers
    from {{ ref('fct_claim') }} c
    join {{ ref('dim_provider') }} p on c.provider_id = p.provider_id
    where c.claim_date >= '2025-01-01'
    group by 1,2
)
select specialty,
       report_month,
       total_claims,
       unique_providers,
       unique_members,
       total_billed_amount,
       total_allowed_amount,
       total_paid_amount,
       case when total_claims>0 then approved_claims::float/total_claims else 0 end as approval_rate,
       case when total_billed_amount>0 then total_allowed_amount/total_billed_amount else 0 end as allowance_ratio,
       case when total_allowed_amount>0 then total_paid_amount/total_allowed_amount else 0 end as payment_ratio,
       denied_claims
from claims
order by report_month, specialty
