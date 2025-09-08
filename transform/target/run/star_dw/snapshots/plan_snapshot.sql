
      
  
    

  create  table "dw"."history"."plan_snapshot"
  
  
    as
  
  (
    
    

    select *,
        md5(coalesce(cast(plan_id as varchar ), '')
         || '|' || coalesce(cast(now()::timestamp without time zone as varchar ), '')
        ) as dbt_scd_id,
        now()::timestamp without time zone as dbt_updated_at,
        now()::timestamp without time zone as dbt_valid_from,
        
  
  coalesce(nullif(now()::timestamp without time zone, now()::timestamp without time zone), null)
  as dbt_valid_to
from (
        

select
  plan_id,
  name,
  metal_tier,
  monthly_premium,
  deductible,
  oop_max,
  coinsurance_rate,
  pcp_copay,
  effective_year,
  load_id,
  load_timestamp
from "dw"."staging"."plans_raw"
    ) sbq



  );
  
  