-- Basic staging model for claims
{{ config(materialized='view') }}

with src as (
    select * from {{ source('staging','claims_raw') }}
)
select
    claim_id,
    member_id,
    provider_id,
    plan_id,
    service_date as claim_date,
    claim_amount,
    allowed_amount,
    paid_amount,
    status as claim_status,
    diagnosis_code,
    procedure_code,
    load_id,
    load_timestamp
from src
