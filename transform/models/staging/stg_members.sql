-- Staging model for members with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'members_raw') }}
),

deduped as (
    select 
        *,
        row_number() over (
            partition by member_id 
            order by member_id
        ) as row_num
    from source
),

final as (
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
        ra_mm,
        year
    from deduped
    where row_num = 1
)

select * from final
