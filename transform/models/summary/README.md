# Summary Layer

These tables are built from the mart layer and are ready for fast use—no need to join or calculate.

Key points:

- Each table is set up for common ways people want to group and filter data (like by month, member, or provider)
- Numbers like totals and averages are already calculated
- Each table has a clear purpose and level (monthly, per member, per provider)

Main tables:

- `agg_claims_monthly`: monthly claim and cost numbers
- `agg_member_cost`: member-level cost and usage
- `agg_provider_performance`: provider performance and cost
- `dashboard_summary`: one-row summary for dashboards

Use these tables when you need fast dashboards or reports that use the same numbers over and over. For new or one-off questions, use the mart or semantic layer instead.

Don’t add tables here for rare questions or very detailed data—keep those in the mart layer.

Start by using the semantic layer for new metrics. If a metric is used a lot, move it here for speed. Clean up old tables when they’re no longer needed.


- Most are materialized as tables for speed; `dashboard_summary` is a view
	- **Materialized tables** are real tables stored in the database. The data is saved and does not need to be recalculated each time you query it. This makes queries much faster.
	- *Example:* `agg_claims_monthly` is a materialized table. When you query it, you get the results instantly because all the totals and counts have already been calculated and stored.
- Each table is built from mart models using `ref()`
- Change a metric here only if it’s stable and used often; experiment in the semantic layer first
