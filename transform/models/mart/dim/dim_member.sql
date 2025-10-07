{{ config(materialized='view', schema='dw') }}
-- Fat dimension with all member attributes including enrollment and behavioral metrics
-- Includes demographic, geographic, clinical, and engagement data for analysis

select
    -- Core demographics
    s.member_id,
    upper(s.first_name) as first_name,
    upper(s.last_name)  as last_name,
    s.dob as date_of_birth,
    s.gender,
    s.age_group,
    
    -- Geographic attributes
    s.region,
    s.state,
    s.geographic_reporting,
    
    -- Plan and enrollment attributes
    s.hios_id,
    s.plan_network_access_type,
    s.plan_metal,
    s.enrollment_length_continuous,
    
    -- Clinical and risk attributes
    s.clinical_segment,
    s.high_cost_member,
    s.mutually_exclusive_hcc_condition,
    s.wisconsin_area_deprivation_index,
    s.ra_mm,
    
    -- Distribution channel attributes
    s.general_agency_name,
    s.broker_name,
    s.sa_contracting_entity_name,
    
    -- Member engagement and behavior
    s.call_count,
    s.app_login_count,
    s.web_login_count,
    s.new_member_in_period,
    s.member_used_app,
    s.member_had_web_login,
    s.member_visited_new_provider_ind,
    
    -- Year for temporal analysis
    s.year,
    
    -- SCD2 attributes
    s.dbt_valid_from as validity_start_ts,
    s.dbt_valid_to   as validity_end_ts,
    (s.dbt_valid_to is null) as is_current
    
from {{ ref('member_snapshot') }} s
where s.dbt_valid_to is null
