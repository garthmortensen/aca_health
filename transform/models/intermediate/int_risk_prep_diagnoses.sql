{{ config(materialized='table') }}

with claims as (
    select * from {{ ref('stg_claims') }}
),

members as (
    select * from {{ ref('int_risk_prep_members') }}
),

icd10_map as (
    select * from {{ ref('hhs_hcc_icd10_to_cc') }}
),

mapped_diagnoses as (
    select
        c.member_id,
        c.diagnosis_code,
        m.age,
        m.gender,
        map.cc,
        map.second_cc,
        map.third_cc,
        map.mce_age_condition,
        map.mce_sex_condition,
        map.cc_age_split,
        map.cc_sex_split
    from claims c
    join members m on c.member_id = m.member_id
    join icd10_map map on replace(c.diagnosis_code, '.', '') = map.icd10
    where map.valid_fy2025 = 'Y'
)

select * from mapped_diagnoses
