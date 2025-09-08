
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    member_id as unique_field,
    count(*) as n_records

from "dw"."dw"."dim_member"
where member_id is not null
group by member_id
having count(*) > 1



  
  
      
    ) dbt_internal_test