
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select claim_amount
from "dw"."dw"."fct_claim"
where claim_amount is null



  
  
      
    ) dbt_internal_test