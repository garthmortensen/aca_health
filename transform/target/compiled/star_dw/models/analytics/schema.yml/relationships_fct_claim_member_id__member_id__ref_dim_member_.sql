
    
    

with child as (
    select member_id as from_field
    from "dw"."dw"."fct_claim"
    where member_id is not null
),

parent as (
    select member_id as to_field
    from "dw"."dw"."dim_member"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


