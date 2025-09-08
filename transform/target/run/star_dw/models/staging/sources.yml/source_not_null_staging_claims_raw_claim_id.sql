
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select claim_id
from "dw"."staging"."claims_raw"
where claim_id is null



  
  
      
    ) dbt_internal_test