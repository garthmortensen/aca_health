
    
    

select
    enrollment_id as unique_field,
    count(*) as n_records

from "dw"."dw"."stg_enrollments"
where enrollment_id is not null
group by enrollment_id
having count(*) > 1


