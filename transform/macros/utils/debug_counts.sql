{% macro debug_counts(limit=5) %}
  {# Build SQL strings by concatenation so ref() resolves before query execution #}
  {% set q1 = run_query('select count(*) as cnt from ' ~ ref('plan_snapshot')) %}
  {% set q2 = run_query('select count(*) as cnt from ' ~ ref('dim_plan')) %}
  {% set q3 = run_query('select count(distinct plan_id) as cnt from ' ~ ref('fct_enrollment')) %}
  {% set q4 = run_query('select plan_id, dbt_valid_from, dbt_valid_to from ' ~ ref('plan_snapshot') ~ ' order by plan_id, dbt_valid_from desc limit ' ~ limit) %}
  {% set q5 = run_query('select e.plan_id, count(*) as fact_rows ' ~
                        'from ' ~ ref('fct_enrollment') ~ ' e left join ' ~ ref('dim_plan') ~ ' p using (plan_id) ' ~
                        'where p.plan_id is null group by 1 order by fact_rows desc') %}
  {% if execute %}
    {{ log('plan_snapshot rows: ' ~ q1.columns[0].values()[0], info=True) }}
    {{ log('dim_plan rows (current filter): ' ~ q2.columns[0].values()[0], info=True) }}
    {{ log('fct_enrollment distinct plan_ids: ' ~ q3.columns[0].values()[0], info=True) }}
    {{ log('Sample snapshot rows (latest first per plan_id ordering):', info=True) }}
    {% for r in q4.rows %}
      {{ log(r, info=True) }}
    {% endfor %}
    {% if q5.rows | length > 0 %}
      {{ log('Missing plan_ids in dim_plan (causing relationship test failures):', info=True) }}
      {% for r in q5.rows %}
        {{ log(r, info=True) }}
      {% endfor %}
    {% else %}
      {{ log('No missing plan_ids detected (relationship test should pass).', info=True) }}
    {% endif %}
  {% endif %}
{% endmacro %}
