

-- Staging: providers
with src as (
  select * from "dw"."staging"."providers_raw"
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