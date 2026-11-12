{{ config(materialized='table', schema='summary') }}

-- Monthly pharmacy utilization and cost by drug class / subclass, normalized
-- to PMPM using member months from enrollment. Paid fills only; rejects and
-- reversals are counted separately so prior authorization friction is visible.

with months as (
    select distinct date_trunc('month', full_date)::date as report_month
    from {{ ref('dim_date') }}
    where full_date between '2022-01-01' and '2025-12-31'
),

member_months as (
    select
        m.report_month,
        count(distinct e.member_id) as member_months
    from months m
    join {{ ref('fct_enrollment') }} e
      on e.start_date <= (m.report_month + interval '1 month' - interval '1 day')::date
     and e.end_date   >= m.report_month
    group by m.report_month
),

fills as (
    select
        date_trunc('month', fill_date)::date as report_month,
        drug_class,
        drug_subclass,
        cost_category,
        is_specialty,
        count(*) filter (where claim_status = 'paid')                       as paid_fills,
        count(*) filter (where claim_status = 'rejected')                   as rejected_claims,
        count(*) filter (where claim_status = 'reversed')                   as reversed_claims,
        count(distinct member_id) filter (where claim_status = 'paid')     as utilizing_members,
        count(*) filter (where claim_status = 'paid' and refill_number = 0) as new_starts,
        sum(days_supply)  filter (where claim_status = 'paid')              as days_supplied,
        sum(plan_paid)    filter (where claim_status = 'paid')              as plan_paid,
        sum(member_copay) filter (where claim_status = 'paid')              as member_copay,
        sum(total_cost)   filter (where claim_status = 'paid')              as total_cost
    from {{ ref('fct_pharmacy_claim') }}
    group by 1, 2, 3, 4, 5
)

select
    f.report_month,
    extract(year from f.report_month)::int as year,
    f.drug_class,
    f.drug_subclass,
    f.cost_category,
    f.is_specialty,
    f.paid_fills,
    f.rejected_claims,
    f.reversed_claims,
    f.utilizing_members,
    f.new_starts,
    f.days_supplied,
    coalesce(f.plan_paid, 0)    as plan_paid,
    coalesce(f.member_copay, 0) as member_copay,
    coalesce(f.total_cost, 0)   as total_cost,
    mm.member_months,
    round(coalesce(f.plan_paid, 0) / nullif(mm.member_months, 0), 2)        as plan_paid_pmpm,
    round(coalesce(f.total_cost, 0) / nullif(mm.member_months, 0), 2)       as total_cost_pmpm,
    round(1000.0 * f.paid_fills / nullif(mm.member_months, 0), 2)           as fills_per_1000_members,
    round(coalesce(f.plan_paid, 0) / nullif(f.paid_fills, 0), 2)            as plan_paid_per_fill,
    round(1.0 * f.utilizing_members / nullif(mm.member_months, 0), 4)       as utilization_rate
from fills f
join member_months mm using (report_month)
order by f.report_month, f.drug_class, f.drug_subclass
