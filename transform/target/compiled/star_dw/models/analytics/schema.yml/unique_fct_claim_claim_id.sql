
    
    

select
    claim_id as unique_field,
    count(*) as n_records

from "dw"."dw"."fct_claim"
where claim_id is not null
group by claim_id
having count(*) > 1


