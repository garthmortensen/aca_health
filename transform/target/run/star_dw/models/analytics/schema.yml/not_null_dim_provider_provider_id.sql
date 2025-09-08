
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select provider_id
from "dw"."dw"."dim_provider"
where provider_id is null



  
  
      
    ) dbt_internal_test