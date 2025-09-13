{{ config(materialized='table') }}

-- Member risk & utilization stratification cube (member x risk buckets)
with base as (
    select m.member_id,
           m.age_group,
           m.gender,
           m.region,
           m.plan_metal,
           m.is_current,
           coalesce(mc.total_paid_amount,0) as total_paid_amount,
           coalesce(mc.total_claims,0) as total_claims,
           coalesce(mc.total_billed_amount,0) as total_billed_amount,
           mc.pmpm_cost,
           mc.cost_category
    from {{ ref('agg_member_cost_cube') }} mc
    join {{ ref('dim_member') }} m using(member_id)
    where m.is_current = true
), risk as (
    select *,
        case 
            when total_paid_amount = 0 then 'No Cost'
            when total_paid_amount < 500 then 'Low'
            when total_paid_amount < 2500 then 'Moderate'
            when total_paid_amount < 10000 then 'High'
            else 'Very High'
        end as paid_risk_bucket,
        case 
            when total_claims = 0 then 'No Util'
            when total_claims <= 2 then 'Low Util'
            when total_claims <= 6 then 'Moderate Util'
            when total_claims <= 15 then 'High Util'
            else 'Very High Util'
        end as utilization_bucket
    from base
)
select member_id,
       age_group,
       gender,
       region,
       plan_metal,
       total_claims,
       total_billed_amount,
       total_paid_amount,
       pmpm_cost,
       cost_category,
       paid_risk_bucket,
       utilization_bucket
from risk
order by total_paid_amount desc
