{{ config(materialized='view', schema='summary') }}

-- Dashboard summary moved to summary schema
with monthly_metrics as (
    select report_month, total_claims, total_paid_amount, unique_members_with_claims, approval_rate
    from {{ ref('agg_claims_monthly') }}
),
cost_distribution as (
    select cost_category, count(member_id) as member_count, sum(total_paid_amount) as category_cost, avg(pmpm_cost) as avg_pmpm
    from {{ ref('agg_member_cost_cube') }}
    group by cost_category
),
provider_summary as (
    select specialty, count(provider_id) as provider_count, sum(total_claims) as specialty_claims, avg(approval_rate) as avg_approval_rate
    from {{ ref('agg_provider_performance') }}
    group by specialty
)
select current_date as report_date,
    (select total_claims from monthly_metrics order by report_month desc limit 1) as latest_month_claims,
    (select total_paid_amount from monthly_metrics order by report_month desc limit 1) as latest_month_cost,
    (select approval_rate from monthly_metrics order by report_month desc limit 1) as latest_approval_rate,
    (select sum(member_count) from cost_distribution) as total_active_members,
    (select member_count from cost_distribution where cost_category = 'High Cost') as high_cost_members,
    (select member_count from cost_distribution where cost_category = 'Very High Cost') as very_high_cost_members,
    round((select sum(category_cost) from cost_distribution where cost_category in ('High Cost', 'Very High Cost'))::numeric / (select sum(category_cost) from cost_distribution) * 100, 2) as high_cost_member_cost_percentage,
    (select count(distinct provider_id) from {{ ref('agg_provider_performance') }}) as total_active_providers,
    (select count(provider_id) from {{ ref('agg_provider_performance') }} where volume_category = 'High Volume') as high_volume_providers,
    (select avg(approval_rate) from {{ ref('agg_provider_performance') }}) as network_avg_approval_rate,
    round(((select total_claims from monthly_metrics order by report_month desc limit 1) - (select total_claims from monthly_metrics order by report_month desc offset 1 limit 1))::numeric / (select total_claims from monthly_metrics order by report_month desc offset 1 limit 1) * 100, 2) as claims_mom_growth_pct,
    round(((select total_paid_amount from monthly_metrics order by report_month desc limit 1) - (select total_paid_amount from monthly_metrics order by report_month desc offset 1 limit 1))::numeric / (select total_paid_amount from monthly_metrics order by report_month desc offset 1 limit 1) * 100, 2) as cost_mom_growth_pct
