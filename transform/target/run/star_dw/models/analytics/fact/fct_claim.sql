
      
        
        
        delete from "dw"."dw"."fct_claim" as DBT_INTERNAL_DEST
        where (claim_id) in (
            select distinct claim_id
            from "fct_claim__dbt_tmp211406260062" as DBT_INTERNAL_SOURCE
        );

    

    insert into "dw"."dw"."fct_claim" ("claim_id", "member_id", "provider_id", "plan_id", "claim_date", "claim_amount", "allowed_amount", "paid_amount", "claim_status", "diagnosis_code", "procedure_code", "load_id", "load_timestamp")
    (
        select "claim_id", "member_id", "provider_id", "plan_id", "claim_date", "claim_amount", "allowed_amount", "paid_amount", "claim_status", "diagnosis_code", "procedure_code", "load_id", "load_timestamp"
        from "fct_claim__dbt_tmp211406260062"
    )
  