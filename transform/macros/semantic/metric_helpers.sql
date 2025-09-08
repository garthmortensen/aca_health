{% macro calculate_pmpm(paid_amount_col, member_months_col) %}
  {# Calculate Per Member Per Month cost #}
  case 
    when {{ member_months_col }} > 0 
    then {{ paid_amount_col }} / {{ member_months_col }}
    else 0 
  end
{% endmacro %}

{% macro calculate_pmpy(pmpm_value) %}
  {# Convert PMPM to Per Member Per Year #}
  {{ pmpm_value }} * 12
{% endmacro %}

{% macro member_months_from_days(coverage_days_col) %}
  {# Convert coverage days to member months (30.44 avg days per month) #}
  {{ coverage_days_col }} / 30.44
{% endmacro %}

{% macro approval_rate(approved_col, total_col) %}
  {# Calculate approval rate with null safety #}
  case 
    when {{ total_col }} > 0 
    then {{ approved_col }}::float / {{ total_col }}
    else 0 
  end
{% endmacro %}

{% macro cost_category(cost_col) %}
  {# Standardized cost categorization #}
  case 
    when {{ cost_col }} = 0 then 'No Claims'
    when {{ cost_col }} <= 500 then 'Low Cost'
    when {{ cost_col }} <= 2000 then 'Moderate Cost'
    when {{ cost_col }} <= 10000 then 'High Cost'
    else 'Very High Cost'
  end
{% endmacro %}

{% macro volume_category(volume_col) %}
  {# Standardized volume categorization #}
  case 
    when {{ volume_col }} >= 100 then 'High Volume'
    when {{ volume_col }} >= 50 then 'Moderate Volume'
    when {{ volume_col }} >= 10 then 'Low Volume'
    else 'Very Low Volume'
  end
{% endmacro %}

{% macro loss_ratio(paid_claims_col, premium_col) %}
  {# Calculate insurance loss ratio (claims paid / premium collected) #}
  case 
    when {{ premium_col }} > 0 
    then {{ paid_claims_col }} / {{ premium_col }}
    else null 
  end
{% endmacro %}

{% macro chronic_condition_filter() %}
  {# Returns SQL for filtering chronic condition diagnosis codes #}
  diagnosis_code in ('4A00', '2B20', 'CA40', 'DA0Z', '5A10', '6A40')
{% endmacro %}

{% macro preventive_care_filter() %}
  {# Returns SQL for filtering preventive care procedure codes #}
  procedure_code in ('99213', '99214', '93000', '80050')
{% endmacro %}

{% macro date_spine(start_date, end_date, grain='month') %}
  {# Generate a date spine for time series analysis #}
  {% if grain == 'month' %}
    with date_spine as (
      select 
        generate_series(
          date_trunc('month', '{{ start_date }}'::date),
          date_trunc('month', '{{ end_date }}'::date),
          '1 month'::interval
        )::date as spine_date
    )
  {% elif grain == 'day' %}
    with date_spine as (
      select 
        generate_series(
          '{{ start_date }}'::date,
          '{{ end_date }}'::date,
          '1 day'::interval
        )::date as spine_date
    )
  {% endif %}
  select * from date_spine
{% endmacro %}

{% macro rolling_metric(metric_col, partition_cols=[], order_col='claim_date', window_size=3) %}
  {# Calculate rolling average over specified window #}
  avg({{ metric_col }}) over (
    {% if partition_cols %}
    partition by {{ partition_cols | join(', ') }}
    {% endif %}
    order by {{ order_col }}
    rows between {{ window_size - 1 }} preceding and current row
  )
{% endmacro %}
