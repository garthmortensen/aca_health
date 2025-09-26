{{ config(materialized='view') }}

with src as (
    select * from {{ source('staging','members_raw') }}
)
select
    member_id,
    first_name,
    last_name,
    dob as date_of_birth,
    gender,
    email,
    phone,
    street,
    city,
    state,
    zip,
    fpl_ratio,
    hios_id,
    plan_network_access_type,
    plan_metal,
    age_group,
    region,
    enrollment_length_continuous,
    clinical_segment,
    general_agency_name,
    broker_name,
    sa_contracting_entity_name,
    call_count,
    app_login_count,
    web_login_count,
    new_member_in_period,
    member_used_app,
    member_had_web_login,
    member_visited_new_provider_ind,
    high_cost_member,
    mutually_exclusive_hcc_condition,
    geographic_reporting,
    wisconsin_area_deprivation_index,
    year,
    load_id,
    load_timestamp
from src
