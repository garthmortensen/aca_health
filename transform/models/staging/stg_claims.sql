-- Staging model for claims with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'claims_raw') }}
    union all
    select * from {{ ref('claims_ebola') }}
    union all
    select * from {{ ref('claims_radiation') }}
),

deduped as (
    select 
        *,
        row_number() over (
            partition by claim_id 
            order by claim_id  -- All rows identical after seed load, no timestamp needed
        ) as row_num
    from source
),

final as (
    select
        claim_id,
        member_id,
        provider_id,
        plan_id,
        service_date as claim_date,
        claim_amount,
        allowed_amount,
        paid_amount,
        status as claim_status,
        diagnosis_code,
        procedure_code,
        -- Additional descriptor/metric primitives
        charges,
        allowed,
        clean_claim_status,
        claim_from,
        clean_claim_out,
        utilization,
        hcg_units_days,
        claim_type,
        major_service_category,
        provider_specialty,
        detailed_service_category,
        ms_drg,
        ms_drg_description,
        ms_drg_mdc,
        ms_drg_mdc_desc,
        cpt,
        cpt_consumer_description,
        procedure_level_1,
        procedure_level_2,
        procedure_level_3,
        procedure_level_4,
        procedure_level_5,
        channel,
        drug_name,
        drug_class,
        drug_subclass,
        drug,
        is_oon,
        best_contracting_entity_name,
        provider_group_name,
        ccsr_system_description,
        ccsr_description
    from deduped
    where row_num = 1
)

select * from final
