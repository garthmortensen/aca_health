
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    enrollment_id as unique_field,
    count(*) as n_records

from "dw"."dw"."stg_enrollments"
where enrollment_id is not null
group by enrollment_id
having count(*) > 1



  
  
      
    ) dbt_internal_test