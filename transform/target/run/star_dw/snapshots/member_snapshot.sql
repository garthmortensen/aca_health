
      
  
    

  create  table "dw"."history"."member_snapshot"
  
  
    as
  
  (
    
    

    select *,
        md5(coalesce(cast(member_id as varchar ), '')
         || '|' || coalesce(cast(now()::timestamp without time zone as varchar ), '')
        ) as dbt_scd_id,
        now()::timestamp without time zone as dbt_updated_at,
        now()::timestamp without time zone as dbt_valid_from,
        
  
  coalesce(nullif(now()::timestamp without time zone, now()::timestamp without time zone), null)
  as dbt_valid_to
from (
        



select
  member_id,
  first_name,
  last_name,
  dob,
  gender,
  email,
  phone,
  street,
  city,
  state,
  zip,
  fpl_ratio,
  plan_metal,
  age_group,
  region,
  load_id,
  load_timestamp
from "dw"."staging"."members_raw"
    ) sbq



  );
  
  