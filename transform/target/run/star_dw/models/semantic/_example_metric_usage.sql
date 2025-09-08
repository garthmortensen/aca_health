
  create view "dw"."dw"."_example_metric_usage__dbt_tmp"
    
    
  as (
    -- Example usage of metric helper macros
-- This shows how the helpers standardize calculations across models

select 
    member_id,
    total_paid_amount,
    coverage_days,
    
    -- Use helper to calculate member months
    
  
  coverage_days / 30.44
 as member_months,
    
    -- Use helper to calculate PMPM
    
  
  case 
    when 
  
  coverage_days / 30.44
 > 0 
    then total_paid_amount / 
  
  coverage_days / 30.44

    else 0 
  end
 as pmpm_cost,
    
    -- Use helper to calculate PMPY  
    
  
  
  
  case 
    when 
  
  coverage_days / 30.44
 > 0 
    then total_paid_amount / 
  
  coverage_days / 30.44

    else 0 
  end
 * 12
 as pmpy_cost,
    
    -- Use helper for standardized cost categorization
    
  
  case 
    when total_paid_amount = 0 then 'No Claims'
    when total_paid_amount <= 500 then 'Low Cost'
    when total_paid_amount <= 2000 then 'Moderate Cost'
    when total_paid_amount <= 10000 then 'High Cost'
    else 'Very High Cost'
  end
 as cost_tier,
    
    -- Use helper for approval rate calculation
    
  
  case 
    when total_claims > 0 
    then approved_claims::float / total_claims
    else 0 
  end
 as member_approval_rate,
    
    -- Use helper for 3-month rolling average of costs
    
  
  avg(total_paid_amount) over (
    
    partition by member_id
    
    order by claim_date
    rows between 2 preceding and current row
  )
 as rolling_3month_cost

from "dw"."dw"."agg_member_cost"
  );