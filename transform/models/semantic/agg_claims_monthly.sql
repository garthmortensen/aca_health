{{ config(materialized='table') }}

-- Monthly claims summary using semantic layer metrics
-- This model demonstrates how to use the semantic layer for reporting
select
    date_trunc('month', claim_date) as report_month,
    count(claim_id) as total_claims,
    sum(claim_amount) as total_billed_amount,
    sum(allowed_amount) as total_allowed_amount,
    sum(paid_amount) as total_paid_amount,
    avg(claim_amount) as avg_claim_amount,
    count(distinct member_id) as unique_members_with_claims,
    count(distinct provider_id) as unique_providers,
    
    -- Calculate key ratios
    case 
        when sum(claim_amount) > 0 
        then sum(allowed_amount) / sum(claim_amount) 
        else 0 
    end as allowance_ratio,
    
    case 
        when sum(allowed_amount) > 0 
        then sum(paid_amount) / sum(allowed_amount) 
        else 0 
    end as payment_ratio,
    
    -- Claims by status
    sum(case when claim_status = 'approved' then 1 else 0 end) as approved_claims,
    sum(case when claim_status = 'denied' then 1 else 0 end) as denied_claims,
    sum(case when claim_status = 'pending' then 1 else 0 end) as pending_claims,
    
    -- Calculate approval rate
    case 
        when count(claim_id) > 0 
        then sum(case when claim_status = 'approved' then 1 else 0 end)::float / count(claim_id) 
        else 0 
    end as approval_rate

from {{ ref('fct_claim') }}
where claim_date >= '2025-01-01'  -- Current year only
group by date_trunc('month', claim_date)
order by report_month
