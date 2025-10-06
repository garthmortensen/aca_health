{% snapshot member_snapshot %}
{#
  This is a dbt SNAPSHOT, not a regular model. A snapshot lets dbt
  keep historical versions of rows (Slowly Changing Dimension Type 2).

  HOW SCD2 HAPPENS HERE (high level):
  1. On the first run, dbt selects all current rows from the source
     table (staging.members_raw) and inserts them into a history table
     (schema: history, table name derived from snapshot name).
  2. Each snapshot run compares the current source row to the latest
     stored version (matching the unique_key = member_id).
  3. If any of the tracked columns (check_cols list below) changed,
     dbt "closes" the existing row by filling dbt_valid_to and inserts
     a brand new row version with a fresh dbt_valid_from and NULL
     dbt_valid_to (meaning current).
  4. If nothing changed, no new row is written.

  KEY COLUMNS dbt ADDS AUTOMATICALLY:
    - dbt_valid_from : timestamp when this version became active.
    - dbt_valid_to   : timestamp when this version stopped being active
                       (NULL means it's the current version).
    - dbt_scd_id     : internal hash key for the version (opaque).

  unique_key:
    Identifies the natural/business key for a member (member_id). All
    versions of the same member share this value.

  strategy = 'check':
    Tells dbt to look ONLY at the columns in check_cols to decide if a
    new version is needed. (Alternative is strategy='timestamp').

  check_cols:
    List of attributes we care about historically. If ANY of these
    values change compared to the latest stored version, SCD2 logic
    triggers a new row.

  HOW TO QUERY CURRENT ROWS LATER:
    select * from history.member_snapshot where dbt_valid_to is null;
    (We already use this pattern in the dim_member model.)

  HOW TO SEE CHANGE HISTORY FOR ONE MEMBER:
    select * from history.member_snapshot where member_id = 'XYZ' order by dbt_valid_from;

  WHAT THIS DOES *NOT* DO:
    - It does not detect deletes (unless the source row disappears AND
      you configure invalidate_hard_deletes — not set here).
    - It does not create surrogate integer keys; we just version rows.

  TL;DR: This file tells dbt: "Track versions of members; if any tracked
  attribute changes, add a new row and timestamp the old one (aka upsert?)." That is SCD2.
#}
{{
  config(
    target_schema='history',
    unique_key='member_id',
    strategy='check',
    check_cols=[
      'first_name','last_name','dob','gender','email','phone','street','city','state','zip',
      'fpl_ratio','plan_metal','age_group','region','ra_mm'
    ]
  )
}}

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
  fpl_ratio,
  plan_metal,
  age_group,
  region,
  ra_mm
from {{ source('staging','members_raw') }}
{% endsnapshot %}
