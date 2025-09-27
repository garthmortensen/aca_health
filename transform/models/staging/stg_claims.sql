-- Basic staging model for claims
{{ config(materialized='view') }}

with latest as (
    select max(load_id) as load_id from {{ source('staging','claims_raw') }}
), src as (
    select * from {{ source('staging','claims_raw') }} where load_id = (select load_id from latest)
)
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
    ccsr_description,
    load_id,
    load_timestamp
from src
