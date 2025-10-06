-- Staging model for enrollments with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'enrollments_raw') }}
),

deduped as (
    select 
        *,
        row_number() over (
            partition by enrollment_id 
            order by enrollment_id
        ) as row_num
    from source
),

final as (
    select
        enrollment_id,
        member_id,
        plan_id,
        start_date,
        end_date,
        (end_date - start_date + 1)::int as coverage_days,
        premium_paid,
        csr_variant
    from deduped
    where row_num = 1
)

select * from final
