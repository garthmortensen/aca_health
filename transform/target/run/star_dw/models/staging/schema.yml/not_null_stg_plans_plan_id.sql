
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select plan_id
from "dw"."dw"."stg_plans"
where plan_id is null



  
  
      
    ) dbt_internal_test