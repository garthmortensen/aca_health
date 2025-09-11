{{ config(materialized='table') }}

-- Provider performance analysis moved to summary schema
with provider_claims as (
    select c.provider_id,
        count(c.claim_id) as total_claims,
        count(distinct c.member_id) as unique_members_served,
        sum(c.claim_amount) as total_billed,
        sum(c.allowed_amount) as total_allowed,
        sum(c.paid_amount) as total_paid,
        avg(c.claim_amount) as avg_claim_amount,
        sum(case when c.claim_status = 'approved' then 1 else 0 end) as approved_claims,
        sum(case when c.claim_status = 'denied' then 1 else 0 end) as denied_claims,
        sum(case when c.claim_status = 'pending' then 1 else 0 end) as pending_claims,
        mode() within group (order by c.diagnosis_code) as most_common_diagnosis,
        mode() within group (order by c.procedure_code) as most_common_procedure
    from {{ ref('fct_claim') }} c
    where c.claim_date >= '2025-01-01'
    group by c.provider_id
),
provider_info as (
    select provider_id, provider_name, specialty, city, state
    from {{ ref('dim_provider') }}
    where is_current = true
)
select p.provider_id, pi.provider_name, pi.specialty, pi.city, pi.state,
    p.total_claims, p.unique_members_served, p.total_billed, p.total_allowed, p.total_paid, p.avg_claim_amount,
    case when p.total_billed > 0 then p.total_allowed / p.total_billed else 0 end as allowance_ratio,
    case when p.total_allowed > 0 then p.total_paid / p.total_allowed else 0 end as payment_ratio,
    case when p.total_claims > 0 then p.approved_claims::float / p.total_claims else 0 end as approval_rate,
    case when p.unique_members_served > 0 then p.total_claims::float / p.unique_members_served else 0 end as claims_per_member,
    case when p.unique_members_served > 0 then p.total_paid / p.unique_members_served else 0 end as cost_per_member,
    p.approved_claims, p.denied_claims, p.pending_claims,
    p.most_common_diagnosis, p.most_common_procedure,
    case when p.total_claims >= 100 then 'High Volume'
         when p.total_claims >= 50 then 'Moderate Volume'
         when p.total_claims >= 10 then 'Low Volume'
         else 'Very Low Volume' end as volume_category,
    case when p.total_paid >= 50000 then 'High Cost'
         when p.total_paid >= 20000 then 'Moderate Cost'
         when p.total_paid >= 5000 then 'Low Cost'
         else 'Very Low Cost' end as cost_category
from provider_claims p
left join provider_info pi on p.provider_id = pi.provider_id
order by p.total_claims desc
