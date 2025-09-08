{% snapshot provider_snapshot %}
{{
  config(
    target_schema='history',
    unique_key='provider_id',
    strategy='check',
    check_cols=['npi','name','specialty','street','city','state','zip','phone']
  )
}}
select
  provider_id,
  npi,
  name,
  specialty,
  street,
  city,
  state,
  zip,
  phone,
  load_id,
  load_timestamp
from {{ source('staging','providers_raw') }}
{% endsnapshot %}
