{{ config(materialized='view') }}

-- Staging: providers
with latest as (
  select max(load_id) as load_id from {{ source('staging','providers_raw') }}
), src as (
  select * from {{ source('staging','providers_raw') }} where load_id = (select load_id from latest)
)
select
  provider_id,
  npi,
  name as provider_name,
  specialty,
  street,
  city,
  state,
  zip,
  phone,
  load_id,
  load_timestamp
from src
