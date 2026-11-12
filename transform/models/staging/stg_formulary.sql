-- Staging model for the formulary (drug list) with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'formulary_raw') }}
),

deduped as (
    select
        *,
        row_number() over (partition by ndc order by ndc) as row_num
    from source
)

select
    ndc,
    drug_name,
    generic_name,
    brand_name,
    drug_class,
    drug_subclass,
    is_generic,
    is_specialty,
    formulary_tier,
    requires_prior_authorization,
    prior_authorization_policy_id,
    quantity_limit_per_fill,
    standard_days_supply,
    wac_per_fill_low,
    wac_per_fill_high
from deduped
where row_num = 1
