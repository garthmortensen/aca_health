
      
        
        
        delete from "dw"."dw"."fct_enrollment" as DBT_INTERNAL_DEST
        where (enrollment_id) in (
            select distinct enrollment_id
            from "fct_enrollment__dbt_tmp211406770249" as DBT_INTERNAL_SOURCE
        );

    

    insert into "dw"."dw"."fct_enrollment" ("enrollment_id", "member_id", "plan_id", "start_date", "end_date", "coverage_days", "premium_paid", "csr_variant", "load_id", "load_timestamp")
    (
        select "enrollment_id", "member_id", "plan_id", "start_date", "end_date", "coverage_days", "premium_paid", "csr_variant", "load_id", "load_timestamp"
        from "fct_enrollment__dbt_tmp211406770249"
    )
  