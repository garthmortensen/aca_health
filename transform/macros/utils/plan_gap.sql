{% macro plan_gap() %}
  {# Diagnostic: show plan_id presence across layers and focus on missing ones in dim_plan #}
  {% set q_staging = run_query('select count(distinct plan_id) as cnt from ' ~ source('staging','plans_raw')) %}
  {% set q_snapshot = run_query('select count(distinct plan_id) as cnt from ' ~ ref('plan_snapshot')) %}
  {% set q_dim = run_query('select count(distinct plan_id) as cnt from ' ~ ref('dim_plan')) %}
  {% set q_enr = run_query('select count(distinct plan_id) as cnt from ' ~ ref('fct_enrollment')) %}
  {% set missing_in_staging = run_query('select distinct e.plan_id from ' ~ ref('fct_enrollment') ~ ' e left join ' ~ source('staging','plans_raw') ~ ' p on e.plan_id = p.plan_id where p.plan_id is null') %}
  {% set missing_in_snapshot = run_query('select distinct s.plan_id from ' ~ source('staging','plans_raw') ~ ' s left join ' ~ ref('plan_snapshot') ~ ' ps on s.plan_id = ps.plan_id where ps.plan_id is null') %}
  {% set missing_in_dim = run_query('select distinct ps.plan_id from ' ~ ref('plan_snapshot') ~ ' ps left join ' ~ ref('dim_plan') ~ ' d on ps.plan_id = d.plan_id where d.plan_id is null') %}
  {% set orphans_fact = run_query('select e.plan_id, count(*) fact_rows from ' ~ ref('fct_enrollment') ~ ' e left join ' ~ ref('dim_plan') ~ ' d using(plan_id) where d.plan_id is null group by 1 order by fact_rows desc') %}
  {% if execute %}
    {{ log('Distinct plan counts -> staging:' ~ q_staging.columns[0].values()[0] ~ ' snapshot:' ~ q_snapshot.columns[0].values()[0] ~ ' dim:' ~ q_dim.columns[0].values()[0] ~ ' fct_enrollment:' ~ q_enr.columns[0].values()[0], info=True) }}
    {% if missing_in_staging.rows %}
      {{ log('Plan IDs used in enrollments but absent in staging.plans_raw:', info=True) }}
      {% for r in missing_in_staging.rows %}{{ log(r, info=True) }}{% endfor %}
    {% endif %}
    {% if missing_in_snapshot.rows %}
      {{ log('Plan IDs present in staging but missing from plan_snapshot:', info=True) }}
      {% for r in missing_in_snapshot.rows %}{{ log(r, info=True) }}{% endfor %}
    {% endif %}
    {% if missing_in_dim.rows %}
      {{ log('Plan IDs present in snapshot but filtered out of dim_plan:', info=True) }}
      {% for r in missing_in_dim.rows %}{{ log(r, info=True) }}{% endfor %}
    {% endif %}
    {% if orphans_fact.rows %}
      {{ log('Orphan plan IDs in fct_enrollment (causing test failure):', info=True) }}
      {% for r in orphans_fact.rows %}{{ log(r, info=True) }}{% endfor %}
    {% else %}
      {{ log('No orphan plan IDs in fct_enrollment.', info=True) }}
    {% endif %}
  {% endif %}
{% endmacro %}
