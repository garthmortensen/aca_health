-- Staging model for plans with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'plans_raw') }}
),

deduped as (
    select 
        *,
        row_number() over (
            partition by plan_id 
            order by plan_id
        ) as row_num
    from source
),

final as (
    select
        plan_id,
        name as plan_name,
        metal_tier,
        monthly_premium::numeric(10,2) as monthly_premium,
        deductible,
        oop_max,
        coinsurance_rate,
        pcp_copay,
        effective_year
    from deduped
    where row_num = 1
)

select * from final
