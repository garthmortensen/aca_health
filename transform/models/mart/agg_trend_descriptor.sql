{{
  config(
    materialized='table',
    schema='dw'
  )
}}

-- Descriptor cube: claim-level dimensions with aggregated metrics for trend analysis
-- Built from fat fact table (fct_claim) and dimensions for proper data warehouse layering
-- Compares 2024 vs 2025 with pre-aggregated metrics for efficient querying

with claims as (
    select * from {{ ref('fct_claim') }}
),

members as (
    select * from {{ ref('dim_member') }}
),

providers as (
    select * from {{ ref('dim_provider') }}
),

claim_data as (
    select
        -- Extract year from service date
        extract(year from c.claim_date) as year,
        
        -- Member identifying dimensions (from members table)
        m.hios_id,
        m.state,
        m.plan_network_access_type,
        m.plan_metal,
        m.age_group,
        m.gender,
        m.region,
        m.clinical_segment,
        m.general_agency_name,
        m.broker_name,
        m.sa_contracting_entity_name,
        m.enrollment_length_continuous,
        
        -- Geographic reporting dimension
        case
            when substr(m.hios_id, 1, 5) = '29341' then 'OHB (Columbus)'
            when substr(m.hios_id, 1, 5) = '45845' then 'OHC (Cleveland Clinic Product)'
            when m.state = 'TX' then concat(m.state, '-', m.plan_network_access_type)
            else m.state
        end as geographic_reporting,
        
        -- Membership flags
        case when m.enrollment_length_continuous <= 5 then 1 else 0 end as new_member_in_period,
        case when m.call_count > 0 then 1 else 0 end as member_called_oscar,
        m.member_used_app,
        m.member_had_web_login,
        m.member_visited_new_provider_ind,
        m.high_cost_member,
        m.mutually_exclusive_hcc_condition,
        m.wisconsin_area_deprivation_index,
        
        -- Claim dimensions
        c.claim_type,
        coalesce(c.major_service_category, 'Unmapped') as major_service_category,
        case
            when c.claim_type = 'RX' then 'Pharmacy'
            else coalesce(p.specialty, 'Unknown')
        end as provider_specialty,
        coalesce(c.detailed_service_category, 'Unmapped') as detailed_service_category,
        case 
            when c.ms_drg is not null 
            then concat(cast(c.ms_drg as text), ' ', coalesce(c.ms_drg_description, ''))
            else 'Unmapped'
        end as ms_drg,
        case 
            when c.ms_drg_mdc is not null 
            then concat(cast(c.ms_drg_mdc as text), ' ', coalesce(c.ms_drg_mdc_desc, ''))
            else 'Unmapped'
        end as ms_drg_mdc,
        c.cpt,
        c.cpt_consumer_description,
        c.procedure_level_1,
        c.procedure_level_2,
        c.procedure_level_3,
        c.procedure_level_4,
        c.procedure_level_5,
        c.channel,
        c.drug_name,
        c.drug_class,
        c.drug_subclass,
        c.drug as drug_name_full,
        c.is_oon as is_out_of_network,
        c.best_contracting_entity_name,
        c.provider_group_name,
        c.ccsr_system_description,
        c.ccsr_description,
        
        -- Metric primitives
        c.clean_claim_status,
        c.charges,
        c.allowed,
        c.claim_from,
        c.clean_claim_out,
        c.utilization,
        c.hcg_units_days,
        c.claim_id
        
    from claims c
    inner join members m on c.member_id = m.member_id
        and extract(year from c.claim_date) = m.year
    left join providers p on c.provider_id = p.provider_id
    where extract(year from c.claim_date) in (2024, 2025)
)

select
    -- All dimension columns
    year,
    hios_id,
    state,
    plan_network_access_type,
    plan_metal,
    age_group,
    gender,
    region,
    geographic_reporting,
    clinical_segment,
    general_agency_name,
    broker_name,
    sa_contracting_entity_name,
    enrollment_length_continuous,
    new_member_in_period,
    member_called_oscar,
    member_used_app,
    member_had_web_login,
    member_visited_new_provider_ind,
    high_cost_member,
    mutually_exclusive_hcc_condition,
    wisconsin_area_deprivation_index,
    claim_type,
    major_service_category,
    provider_specialty,
    detailed_service_category,
    ms_drg,
    ms_drg_mdc,
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
    drug_name_full,
    is_out_of_network,
    best_contracting_entity_name,
    provider_group_name,
    ccsr_system_description,
    ccsr_description,
    
    -- Aggregated metrics
    sum(case when clean_claim_status = 'PAID' then charges else 0 end) as charges,
    sum(case when clean_claim_status != 'PAID' then charges else 0 end) as denied_charges,
    sum(allowed) as allowed,
    count(distinct case when clean_claim_status = 'DENIED' then claim_id end) as count_of_denied_claims,
    count(distinct claim_id) as count_of_claims,
    sum(case when is_out_of_network = 1 then allowed else 0 end) as out_of_network_allowed,
    sum(utilization) as utilization,
    sum(hcg_units_days) as units_days,
    avg(
        case 
            when clean_claim_status = 'PAID' and clean_claim_out is not null
            then clean_claim_out::date - claim_from::date
            else null
        end
    ) as avg_days_service_to_paid

from claim_data
group by 
    year, hios_id, state, plan_network_access_type, plan_metal, age_group, gender,
    region, geographic_reporting, clinical_segment, general_agency_name, broker_name,
    sa_contracting_entity_name, enrollment_length_continuous, new_member_in_period,
    member_called_oscar, member_used_app, member_had_web_login, 
    member_visited_new_provider_ind, high_cost_member, mutually_exclusive_hcc_condition,
    wisconsin_area_deprivation_index, claim_type, major_service_category, provider_specialty,
    detailed_service_category, ms_drg, ms_drg_mdc, cpt, cpt_consumer_description,
    procedure_level_1, procedure_level_2, procedure_level_3, procedure_level_4,
    procedure_level_5, channel, drug_name, drug_class, drug_subclass, drug_name_full,
    is_out_of_network, best_contracting_entity_name, provider_group_name,
    ccsr_system_description, ccsr_description
