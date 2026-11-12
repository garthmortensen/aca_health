{{ config(materialized='table', schema='summary') }}

-- Monthly prior authorization throughput by policy: volume, approval rate,
-- turnaround, time to first fill, and why requests were denied.

select
    date_trunc('month', request_date)::date as report_month,
    extract(year from request_date)::int    as year,
    policy_id,
    drug_subclass,
    count(*)                                                         as requests,
    count(*) filter (where decision = 'approved')                    as approved,
    count(*) filter (where decision = 'denied')                      as denied,
    round(count(*) filter (where decision = 'approved')::numeric
          / nullif(count(*), 0), 4)                                  as approval_rate,
    count(*) filter (where urgency = 'expedited')                    as expedited_requests,
    round(avg(turnaround_days), 2)                                   as avg_turnaround_days,
    round(avg(turnaround_days) filter (where urgency = 'standard'), 2)  as avg_turnaround_standard,
    round(avg(turnaround_days) filter (where urgency = 'expedited'), 2) as avg_turnaround_expedited,
    count(*) filter (where first_fill_date is not null)              as approved_and_filled,
    round(avg(days_to_first_fill), 2)                                as avg_days_to_first_fill,
    round(avg(request_date - hba1c_date) filter (where hba1c_date is not null), 1) as avg_days_since_hba1c,
    count(*) filter (where primary_denial_category = 'Step therapy not met')       as denied_step_therapy,
    count(*) filter (where primary_denial_category = 'Clinical threshold not met') as denied_clinical_threshold,
    count(*) filter (where primary_denial_category = 'Diagnosis not supported')    as denied_diagnosis,
    count(*) filter (where primary_denial_category = 'Age criterion')              as denied_age,
    count(*) filter (where primary_denial_category = 'Contraindication')           as denied_contraindication,
    count(*) filter (where prescriber_specialty = 'Family Medicine')               as requests_from_primary_care
from {{ ref('fct_prior_authorization_request') }}
group by 1, 2, 3, 4
order by 1, 3
