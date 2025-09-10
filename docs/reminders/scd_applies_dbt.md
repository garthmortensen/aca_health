# SCD & Dimensional Modeling (dbt-centric Version)

This version re-frames the earlier SCD design around dbt conventions (sources, staging models, incremental dims, snapshots, tests).

---
## 1. Overall Layering (dbt Folders)
```
models/
  sources/          # source.yml (staging.* tables)
  staging/          # cleaned, typed selects (stg_*)
  dims/             # dim_* (incremental SCD2 or snapshot-fed)
  facts/            # fact_* (incremental)
  marts/            # aggregates / rollups
snapshots/          # Optional dbt snapshot definitions for SCD2
macros/             # hashdiff, surrogate key helpers
seeds/              # (If you add static code sets, date spine)
```

---
## 2. Choose SCD2 Mechanism
Two primary dbt approaches:

| Approach | When to use | Pros | Cons |
|----------|-------------|------|------|
| dbt Snapshots | Source tables change in place (OLTP style) | Built-in validity window logic | Two-step (snapshot table separate from dim) |
| Incremental Model (custom logic) | Append-only staging (your case) | Single table (dim) directly built | You must code hashdiff + merge yourself |

Your staging pattern (new load_id each batch, immutable prior rows) → Prefer incremental model with MERGE / delete+insert logic.

---
## 3. Standard Hashdiff Macro
`macros/hash.sql`:
```sql
{% raw %}
{% macro hashdiff(cols) %}
  md5(concat_ws('||'{% for c in cols %}, coalesce(trim(cast({{ c }} as text)),'') {% endfor %}))
{% endmacro %}
{% endraw %}
```
(Use md5 for brevity; upgrade to sha256 if desired.)

---
## 4. Sources Definition (example)
`models/sources/staging_sources.yml`:
```yaml
version: 2
sources:
  - name: staging
    schema: staging
    tables:
      - name: members_raw
      - name: plans_raw
      - name: providers_raw
      - name: enrollments_raw
      - name: claims_raw
```

---
## 5. Staging Model Pattern
`models/staging/stg_members.sql`:
```sql
{% raw %}
with src as (
  select *, load_id from {{ source('staging','members_raw') }}
)
select
  member_id,
  first_name,
  last_name,
  dob,
  gender,
  email,
  phone,
  street,
  city,
  state,
  zip,
  region,
  fpl_ratio,
  clinical_segment,
  plan_metal,
  year,
  load_id,
  {{ hashdiff(['first_name','last_name','dob','gender','street','city','state','zip','region','fpl_ratio','clinical_segment','plan_metal']) }} as scd2_hash
from src;
{% endraw %}
```
Add tests (unique, not_null) in a `stg_members.yml` if needed.

---
## 6. Incremental SCD2 Dimension (DimMember)
`models/dims/dim_member.sql`:
```sql
{% raw %}
{{ config(
    materialized='incremental',
    unique_key='member_id||valid_from',
    on_schema_change='ignore'
) }}

{% set tracked_cols = [
  'first_name','last_name','dob','gender','street','city','state','zip','region','fpl_ratio','clinical_segment','plan_metal'
] %}

with incoming as (
  select *, current_timestamp as as_of
  from {{ ref('stg_members') }}
), latest_change as (
  -- identify rows that are new or changed vs current active
  select i.*
  from incoming i
  left join {{ this }} d
    on d.member_id = i.member_id
   and d.is_current = true
  where d.member_id is null            -- brand new
     or d.scd2_hash <> i.scd2_hash     -- changed attributes
), expired as (
  select d.member_sk
  from {{ this }} d
  join latest_change c
    on d.member_id = c.member_id
   and d.is_current = true
)

-- 1) Expire current rows (only in incremental runs)
{% if is_incremental() %}
  update {{ this }}
     set valid_to = current_date, is_current = false
   where member_sk in (select member_sk from expired);
{% endif %}

-- 2) Insert new versions
select
  nextval(pg_get_serial_sequence('{{ this }}','member_sk')) as member_sk,
  member_id,
  first_name,
  last_name,
  dob,
  gender,
  email,
  phone,
  street,
  city,
  state,
  zip,
  region,
  fpl_ratio,
  clinical_segment,
  plan_metal,
  scd2_hash,
  current_date as valid_from,
  date '9999-12-31' as valid_to,
  true as is_current
from latest_change
{% endraw %}
```
(You may alternatively use a MERGE if your warehouse dialect supports it; Postgres in dbt 1.9 allows `strategy='merge'` config.)

Add initial table creation seed (empty) or run once without incremental flag.

---
## 7. Other Dimensions
Replicate the above pattern for Plan & Provider (change tracked columns + natural key). Include `effective_year` in hash / unique key for Plan.

---
## 8. Date Dimension via Seed or Model
Option A: Seed file `seeds/date_spine.csv` (pre-generated). Option B: SQL model generating series:
```sql
{% raw %}
{{ config(materialized='table') }}
with dates as (
  select generate_series(date '2018-01-01', date '2030-12-31', interval '1 day')::date as d
)
select
  to_char(d,'YYYYMMDD')::int as date_sk,
  d as date_actual,
  extract(year from d)::int as year,
  extract(month from d)::int as month,
  extract(day from d)::int as day,
  to_char(d,'YYYY-MM') as year_month
from dates;
{% endraw %}
```

---
## 9. Fact Model (FactClaim)
`models/facts/fact_claim.sql`:
```sql
{% raw %}
{{ config(materialized='incremental', unique_key='claim_id') }}

with src as (
  select * from {{ source('staging','claims_raw') }}
), dim_member as (
  select member_id, member_sk
  from {{ ref('dim_member') }} where is_current
), dim_plan as (
  select plan_id, effective_year, plan_sk
  from {{ ref('dim_plan') }} where is_current
), dim_provider as (
  select provider_id, provider_sk
  from {{ ref('dim_provider') }} where is_current
), resolved as (
  select
    c.claim_id,
    c.service_date,
    to_char(c.service_date,'YYYYMMDD')::int as service_date_sk,
    m.member_sk,
    p.plan_sk,
    pr.provider_sk,
    c.claim_amount,
    c.allowed_amount,
    c.paid_amount,
    c.status,
    c.diagnosis_code,
    c.procedure_code
  from src c
  left join dim_member m   on m.member_id = c.member_id
  left join dim_plan   p   on p.plan_id = c.plan_id and p.effective_year = extract(year from c.service_date)
  left join dim_provider pr on pr.provider_id = c.provider_id
  where m.member_sk is not null -- enforce referential integrity
)
select * from resolved
{% if is_incremental() %}
 where claim_id not in (select claim_id from {{ this }})
{% endif %}
{% endraw %}
```

---
## 10. Tests (Example YAML)
`models/facts/fact_claim.yml`:
```yaml
version: 2
models:
  - name: fact_claim
    tests:
      - unique:
          column_name: claim_id
      - not_null:
          column_name: claim_id
    columns:
      - name: member_sk
        tests: [not_null]
      - name: plan_sk
        tests: [not_null]
      - name: provider_sk
        tests: [not_null]
```
Add exposure or metric definitions later if adopting dbt semantic layer.

---
## 11. Snapshot Alternative (If You Switch)
Example snapshot (if upstream rows mutate rather than append):
`snapshots/member_snapshot.sql`:
```sql
{% raw %}
{% snapshot member_snapshot %}
{{ config(
  target_schema='snapshots',
  unique_key='member_id',
  strategy='check',
  check_cols=['first_name','last_name','street','city','state','zip','region','fpl_ratio','clinical_segment','plan_metal']
) }}
select * from {{ source('staging','members_raw') }}
{% endsnapshot %}
{% endraw %}
```
Then build `dim_member` off latest snapshot rows or transform snapshot table into Type 2 final dimension.

---
## 12. Run Order
```
dbt run --select sources:staging
dbt run --select staging
# Dimensions first (SCD2 incrementals)
dbt run --select dims
# Facts after dimensions
dbt run --select facts
# Tests
dbt test
```
(Or just `dbt build` once everything configured.)

---
## 13. Handling Late Arriving Facts
- Option: keep a `fact_claim_staging` model (ephemeral) filtering unmatched dimension keys to a warning table.
- Add a dimension row with `member_id='UNKNOWN'` etc. and default surrogate key for strict joins.

---
## 14. Performance / Maintenance
- Periodically `VACUUM ANALYZE` dimensions & facts (outside dbt) if Postgres.
- Add indexes on surrogate keys (dbt `post-hook` or manual DDL).
- Consider partitioning large facts by service_date (future). 

---
## 15. Summary Choices Adopted Here
- Incremental SCD2 via custom logic (no snapshots initially).
- Hashdiff for change detection.
- Facts incremental with natural key anti-join.
- Date dimension as generated table model.
- Referential integrity enforced in fact model filters + tests.

Adapt counts & hash columns as requirements evolve.
