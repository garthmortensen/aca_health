{% macro run_sql(sql) %}
  {#
    Simple helper to execute ad-hoc SQL via:
      dbt run-operation run_sql --args '{"sql": "select 1 as x"}'
    Returns a table (list of dict rows) so you can inspect in logs.
  #}
  {% set results = run_query(sql) %}
  {% if execute %}
    {{ log("run_sql rows=" ~ results.rows | length, info=True) }}
    {% for row in results.rows %}
      {{ log(row, info=True) }}
    {% endfor %}
  {% endif %}
  {{ return(results) }}
{% endmacro %}
