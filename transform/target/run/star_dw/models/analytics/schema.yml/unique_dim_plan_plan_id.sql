
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    plan_id as unique_field,
    count(*) as n_records

from "dw"."dw"."dim_plan"
where plan_id is not null
group by plan_id
having count(*) > 1



  
  
      
    ) dbt_internal_test