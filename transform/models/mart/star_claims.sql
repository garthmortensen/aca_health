{{ config(materialized='table') }}
-- Central star schema joining claim facts to all dimensions
with fct_claim as (
    select * from {{ ref('fct_claim') }}
),
member as (
    select * from {{ ref('dim_member') }}
),
plan as (
    select * from {{ ref('dim_plan') }}
),
provider as (
    select * from {{ ref('dim_provider') }}
),
date_dim as (
    select * from {{ ref('dim_date') }}
)
select
    c.claim_id,
    c.claim_date,
    d.full_date as claim_full_date,
    c.member_id,
    m.first_name as member_first_name,
    m.last_name as member_last_name,
    m.date_of_birth as member_dob,
    m.gender as member_gender,
    m.age_group as member_age_group,
    m.region as member_region,
    c.plan_id,
    p.plan_name,
    p.metal_tier,
    p.monthly_premium,
    c.provider_id,
    pr.provider_name,
    pr.specialty as provider_specialty,
    c.claim_amount,
    c.allowed_amount,
    c.paid_amount,
    c.claim_status,
    c.diagnosis_code,
    c.procedure_code,
    c.load_id,
    c.load_timestamp
from fct_claim c
left join member m on c.member_id = m.member_id
left join plan p on c.plan_id = p.plan_id
left join provider pr on c.provider_id = pr.provider_id
left join date_dim d on c.claim_date = d.full_date
