{{ config(materialized='incremental', unique_key='pharmacy_claim_id', schema='dw') }}
-- Pharmacy claim fact: one row per fill attempt (paid, reversed, or rejected).
-- Kept separate from fct_claim because pharmacy claims carry a different grain
-- (NDC, days supply, refill number, reject codes) and are adjudicated by the PBM.

with claims as (
    select * from {{ ref('stg_pharmacy_claims') }}
),
dim_member as (
    select member_id from {{ ref('dim_member') }}
),
formulary as (
    select ndc, cost_category from {{ ref('dim_formulary') }}
)

select
    c.pharmacy_claim_id,
    c.member_id,
    c.plan_id,
    c.prescriber_id,
    c.pharmacy_npi,
    c.pharmacy_name,
    c.channel,
    c.fill_date,

    -- Drug
    c.ndc,
    c.drug_name,
    c.generic_name,
    c.brand_name,
    c.drug_class,
    c.drug_subclass,
    c.is_generic,
    c.is_specialty,
    c.formulary_tier,
    f.cost_category,

    -- Utilization
    c.days_supply,
    c.quantity,
    c.refill_number,
    (c.refill_number = 0) as is_new_start,

    -- Financials (zero for rejected and reversed claims)
    c.ingredient_cost,
    c.dispensing_fee,
    c.member_copay,
    c.plan_paid,
    c.total_cost,

    -- Adjudication
    c.claim_status,
    (c.claim_status = 'paid') as is_paid,
    c.reject_code,
    c.reject_description,
    c.prior_authorization_request_id

from claims c
left join dim_member dm using (member_id)
left join formulary f using (ndc)
