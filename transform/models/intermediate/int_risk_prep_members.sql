{{ config(materialized='table') }}

with members as (
    select * from {{ ref('stg_members') }}
),

final as (
    select
        member_id,
        gender,
        date_of_birth,
        -- Calculate age as of the benefit year (assuming 2025 for now based on context)
        -- In reality, this should be dynamic based on the enrollment year.
        -- Using 2025 as the benefit year.
        2025 - extract(year from date_of_birth) as age,
        plan_metal,
        -- CSR logic would go here if we had CSR indicator. Assuming standard for now.
        case 
            when plan_metal = 'Platinum' then 'Platinum'
            when plan_metal = 'Gold' then 'Gold'
            when plan_metal = 'Silver' then 'Silver'
            when plan_metal = 'Bronze' then 'Bronze'
            when plan_metal = 'Catastrophic' then 'Catastrophic'
            else 'Silver' -- Default
        end as metal_level
    from members
)

select * from final
