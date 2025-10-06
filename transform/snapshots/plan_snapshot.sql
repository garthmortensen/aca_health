{% snapshot plan_snapshot %}
{{
  config(
    target_schema='history',
    unique_key='plan_id',
    strategy='check',
    check_cols=['name','metal_tier','monthly_premium','deductible','oop_max','coinsurance_rate','pcp_copay','effective_year']
  )
}}
select
  plan_id,
  name,
  metal_tier,
  monthly_premium,
  deductible,
  oop_max,
  coinsurance_rate,
  pcp_copay,
  effective_year
from {{ source('staging','plans_raw') }}
{% endsnapshot %}
