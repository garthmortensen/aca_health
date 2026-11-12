-- Staging model for pharmacy claims with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'pharmacy_claims_raw') }}
),

deduped as (
    select
        *,
        row_number() over (
            partition by pharmacy_claim_id
            order by pharmacy_claim_id
        ) as row_num
    from source
),

final as (
    select
        pharmacy_claim_id,
        member_id,
        plan_id,
        prescriber_id,
        pharmacy_npi,
        pharmacy_name,
        channel,
        fill_date,
        ndc,
        drug_name,
        generic_name,
        brand_name,
        drug_class,
        drug_subclass,
        is_generic,
        is_specialty,
        formulary_tier,
        days_supply,
        quantity,
        refill_number,
        ingredient_cost,
        dispensing_fee,
        member_copay,
        plan_paid,
        (ingredient_cost + dispensing_fee) as total_cost,
        claim_status,
        reject_code,
        reject_description,
        prior_authorization_request_id
    from deduped
    where row_num = 1
)

select * from final
