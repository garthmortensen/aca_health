{{ config(materialized='incremental', unique_key='claim_id', schema='dw') }}
-- Fat fact table with all descriptor fields for efficient analysis
-- Includes claim metrics and dimensional attributes from staging

with claims as (
    select * from {{ ref('stg_claims') }}
), 
dim_member as (
    select member_id from {{ ref('dim_member') }}
)

select
    -- Core fact keys and metrics
    c.claim_id,
    c.member_id,
    c.provider_id,
    c.plan_id,
    c.claim_date,
    c.claim_amount,
    c.allowed_amount,
    c.paid_amount,
    c.claim_status,
    c.diagnosis_code,
    c.procedure_code,
    
    -- Additional descriptor/metric primitives for trend analysis
    c.charges,
    c.allowed,
    c.clean_claim_status,
    c.claim_from,
    c.clean_claim_out,
    c.utilization,
    c.hcg_units_days,
    
    -- Claim type and service categorization
    c.claim_type,
    c.major_service_category,
    c.provider_specialty,
    c.detailed_service_category,
    
    -- MS-DRG and MDC codes
    c.ms_drg,
    c.ms_drg_description,
    c.ms_drg_mdc,
    c.ms_drg_mdc_desc,
    
    -- CPT codes and procedure hierarchy
    c.cpt,
    c.cpt_consumer_description,
    c.procedure_level_1,
    c.procedure_level_2,
    c.procedure_level_3,
    c.procedure_level_4,
    c.procedure_level_5,
    
    -- Place of service
    c.channel,
    
    -- Pharmacy/Drug information
    c.drug_name,
    c.drug_class,
    c.drug_subclass,
    c.drug,
    
    -- Network and contracting
    c.is_oon,
    c.best_contracting_entity_name,
    c.provider_group_name,
    
    -- Clinical classification (CCSR)
    c.ccsr_system_description,
    c.ccsr_description

from claims c
left join dim_member dm using (member_id)
