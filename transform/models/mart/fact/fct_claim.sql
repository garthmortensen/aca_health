{{ config(materialized='incremental', unique_key='claim_id', schema='dw') }}
-- moved from analytics to mart
with claims as (
    select * from {{ ref('stg_claims') }}
), dim_member as (
    select member_id from {{ ref('dim_member') }}
)
select
    c.claim_id,
    c.member_id,
    c.provider_id,
    c.plan_id,
    c.claim_date,
    c.claim_amount,
    c.allowed_amount,
    c.paid_amount,
    c.claim_status,
    c.diagnosis_code,
    c.procedure_code,
    c.load_id,
    c.load_timestamp
from claims c
left join dim_member dm using (member_id)

{% if is_incremental() %}
where c.load_timestamp > (select coalesce(max(load_timestamp), '1900-01-01') from {{ this }})
{% endif %}
