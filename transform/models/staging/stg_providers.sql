-- Staging model for providers with deduplication
{{ config(materialized='view', schema='staging') }}

with source as (
    select * from {{ source('staging', 'providers_raw') }}
),

deduped as (
    select 
        *,
        row_number() over (
            partition by provider_id 
            order by provider_id
        ) as row_num
    from source
),

final as (
    select
        provider_id,
        npi,
        name as provider_name,
        specialty,
        street,
        city,
        state,
        zip,
        phone
    from deduped
    where row_num = 1
)

select * from final
