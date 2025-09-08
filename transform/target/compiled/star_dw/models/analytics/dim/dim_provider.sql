
-- Current provider dimension rows derived from snapshot (SCD2 readiness)
select
    s.provider_id,
    s.npi,
    upper(s.name) as provider_name,
    s.specialty,
    s.street,
    s.city,
    s.state,
    s.zip,
    s.phone,
    s.load_id,
    s.dbt_valid_from as validity_start_ts,
    s.dbt_valid_to   as validity_end_ts,
    (s.dbt_valid_to is null) as is_current
from "dw"."history"."provider_snapshot" s
where s.dbt_valid_to is null