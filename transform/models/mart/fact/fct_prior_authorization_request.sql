{{ config(materialized='incremental', unique_key='prior_authorization_request_id', schema='dw') }}
-- Prior authorization fact: one row per request, with outcome, turnaround, and
-- the clinical facts the decision rested on.

with requests as (
    select * from {{ ref('stg_prior_authorization_requests') }}
),
dim_member as (
    select member_id from {{ ref('dim_member') }}
),
formulary as (
    select ndc, drug_class, drug_subclass, formulary_tier, is_specialty from {{ ref('dim_formulary') }}
)

select
    r.prior_authorization_request_id,
    r.member_id,
    r.plan_id,
    r.prescriber_id,
    r.prescriber_specialty,
    r.policy_id,
    r.ndc,
    r.drug_name,
    f.drug_class,
    f.drug_subclass,
    f.formulary_tier,
    f.is_specialty,

    -- Timeline
    r.request_date,
    r.decision_date,
    r.turnaround_days,
    r.urgency,
    r.first_fill_date,
    r.days_to_first_fill,

    -- Outcome
    r.decision,
    (r.decision = 'approved') as is_approved,
    r.denial_reasons,
    case
        when r.denial_reasons is null then null
        when r.denial_reasons like '%step_%' then 'Step therapy not met'
        when r.denial_reasons like '%hba1c%' or r.denial_reasons like '%bmi%' or r.denial_reasons like '%lifestyle%' then 'Clinical threshold not met'
        when r.denial_reasons like '%diagnosis%' then 'Diagnosis not supported'
        when r.denial_reasons like '%age%' then 'Age criterion'
        when r.denial_reasons like '%thyroid%' or r.denial_reasons like '%another_glp1%' then 'Contraindication'
        else 'Other'
    end as primary_denial_category,

    -- Clinical facts
    r.diagnosis_code,
    r.age_at_request,
    r.has_type2_diabetes_diagnosis,
    r.has_rheumatoid_arthritis_diagnosis,
    r.hba1c_percent,
    r.hba1c_date,
    r.bmi,
    r.weight_comorbidities,
    r.weight_comorbidity_count,
    r.lifestyle_program_months,
    r.prior_therapy_drug,
    r.prior_therapy_days,
    r.prior_therapy_start_date,
    r.prior_therapy_intolerance,
    r.medullary_thyroid_cancer_history,
    r.taking_another_glp1,
    r.tuberculosis_screen_negative,
    r.rheumatology_consult

from requests r
left join dim_member dm using (member_id)
left join formulary f using (ndc)
