-- Staging model for prior authorization requests with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'prior_authorization_requests_raw') }}
),

deduped as (
    select
        *,
        row_number() over (
            partition by prior_authorization_request_id
            order by prior_authorization_request_id
        ) as row_num
    from source
),

final as (
    select
        prior_authorization_request_id,
        member_id,
        plan_id,
        prescriber_id,
        prescriber_specialty,
        policy_id,
        ndc,
        drug_name,
        request_date,
        decision_date,
        turnaround_days,
        urgency,
        decision,
        denial_reasons,
        first_fill_date,
        (first_fill_date - decision_date) as days_to_first_fill,
        diagnosis_code,
        age_at_request,
        -- Clinical facts that decided the request (the answer key for note review)
        has_type2_diabetes_diagnosis,
        has_rheumatoid_arthritis_diagnosis,
        hba1c_percent,
        hba1c_date,
        bmi,
        weight_comorbidities,
        weight_comorbidity_count,
        lifestyle_program_months,
        prior_therapy_drug,
        prior_therapy_days,
        prior_therapy_start_date,
        prior_therapy_intolerance,
        medullary_thyroid_cancer_history,
        taking_another_glp1,
        tuberculosis_screen_negative,
        rheumatology_consult
    from deduped
    where row_num = 1
)

select * from final
