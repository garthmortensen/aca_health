
    
    

select
    member_id as unique_field,
    count(*) as n_records

from "dw"."dw"."stg_members"
where member_id is not null
group by member_id
having count(*) > 1


