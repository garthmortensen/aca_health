{{
  config(
    materialized='table',
    schema='dw'
  )
}}

-- Norm cube: member-level dimensions with enrollment metrics for normalization
-- Built from fat dimension table (dim_member) for proper data warehouse layering
-- Used to calculate PMPM and other normalized rates for 2024 vs 2025 comparison

with members as (
    select * from {{ ref('dim_member') }}
),

member_data as (
    select
        -- Year dimension
        year,
        
        -- Identifying dimensions
        hios_id,
        state,
        plan_network_access_type,
        plan_metal,
        age_group,
        gender,
        region,
        
        -- Geographic reporting dimension
        case
            when substr(hios_id, 1, 5) = '29341' then 'OHB (Columbus)'
            when substr(hios_id, 1, 5) = '45845' then 'OHC (Cleveland Clinic Product)'
            when state = 'TX' then concat(state, '-', plan_network_access_type)
            else state
        end as geographic_reporting,
        
        -- Member attributes
        clinical_segment,
        general_agency_name,
        broker_name,
        sa_contracting_entity_name,
        enrollment_length_continuous,
        
        -- Member behavior flags
        case when enrollment_length_continuous <= 5 then 1 else 0 end as new_member_in_period,
        case when call_count > 0 then 1 else 0 end as member_called_oscar,
        member_used_app,
        member_had_web_login,
        member_visited_new_provider_ind,
        high_cost_member,
        mutually_exclusive_hcc_condition,
        wisconsin_area_deprivation_index,
        
        -- Metrics for aggregation
        ra_mm,
        member_id
        
    from members
    where year in (2024, 2025)
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
    
    -- Aggregated metrics
    sum(ra_mm) as member_months,
    count(distinct member_id) as unique_members_enrolled

from member_data
group by 
    year, hios_id, state, plan_network_access_type, plan_metal, age_group, gender,
    region, geographic_reporting, clinical_segment, general_agency_name, broker_name,
    sa_contracting_entity_name, enrollment_length_continuous, new_member_in_period,
    member_called_oscar, member_used_app, member_had_web_login, 
    member_visited_new_provider_ind, high_cost_member, mutually_exclusive_hcc_condition,
    wisconsin_area_deprivation_index
