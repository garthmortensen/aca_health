
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select load_id
from "dw"."staging"."load_batches"
where load_id is null



  
  
      
    ) dbt_internal_test