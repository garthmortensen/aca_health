
  create view "dw"."dw"."stg_members__dbt_tmp"
    
    
  as (
    

with src as (
    select * from "dw"."staging"."members_raw"
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
    new_member_in_period,
    member_used_app,
    member_had_web_login,
    member_visited_new_provider_ind,
    high_cost_member,
    mutually_exclusive_hcc_condition,
    geographic_reporting,
    year,
    load_id,
    load_timestamp
from src
  );