
      
  
    

  create  table "dw"."history"."provider_snapshot"
  
  
    as
  
  (
    
    

    select *,
        md5(coalesce(cast(provider_id as varchar ), '')
         || '|' || coalesce(cast(now()::timestamp without time zone as varchar ), '')
        ) as dbt_scd_id,
        now()::timestamp without time zone as dbt_updated_at,
        now()::timestamp without time zone as dbt_valid_from,
        
  
  coalesce(nullif(now()::timestamp without time zone, now()::timestamp without time zone), null)
  as dbt_valid_to
from (
        

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
from "dw"."staging"."providers_raw"
    ) sbq



  );
  
  