Project flow to organize the data warehouse.

# 1) Start with questions → pick events (facts) + grain

* **Fact** = numeric event you aggregate (claims paid, premiums).
* **Grain** = “one row equals what?” (per claim line, per member-month, etc).

For health insurance, a solid starter set:

* **fact\_claim\_line** (grain: one claim line on the service date). Measures: claim\_amount, allowed\_amount, paid\_amount.
* **fact\_premium\_payment** (grain: one member-month payment). Measures: premium\_billed, premium\_paid.
* **fact\_enrollment\_episode** (accumulating snapshot: one row per member–plan coverage episode; starts open, you fill end\_date/termination later).
* **fact\_member\_month** (periodic snapshot: one row per member per month enrolled; for counts, churn, PMPM).

# 2) List dimensions (who/what/where/when) and assign keys

* **Surrogate key (SK)** = warehouse int ID (joins are fast, SCD works). This is the primary key in dimension tables.
* **Natural key (NK)** = business ID (member\_id, npi, hios\_id).
* Core dims:

  * **dim\_member** (NK: member\_id)
  * **dim\_plan** (NK: plan\_id + effective\_year **or** hios\_id + csr\_variant)
  * **dim\_provider** (NK: npi)
  * **dim\_date** (calendar)
  * **dim\_geography** (derived from ZIP/county/state)
  * Small/junk dims: **dim\_csr**, **dim\_claim\_status**, etc.
  * Code sets: **dim\_diagnosis**, **dim\_procedure** (ICD/CPT; mostly static)

Conformed dims = reused across facts (same dim\_member joins to claims and premium facts).

# 3) SCD scope per dimension

- **Type 0 (SCD0)** = never change (treat as constant)
- **Type 1 (SCD1)** = overwrite value (lose history)
- **Type 2 (SCD2)** = add a new row w/ date range (keep history)
- **Type 3 (SCD3)** = keep current + one previous value (rare)
- **Type 4 (SCD4)** = history in separate archive table (rare)
- **Type 6 (SCD6)** = hybrid of 1 + 2 (+ optional previous col)

Suggested, practical defaults:

**dim\_member (NK: member\_id)**

* 0: dob, gender (true “identity” attributes)
* 1: email, phone (correct bad data—usually not analytic history)
* 2: address, city, state, zip, region, fpl\_ratio, clinical\_segment (you usually need history)

**dim\_plan (NK: plan\_id + effective\_year or hios\_id + csr)**

* Plans change each plan year. Make **effective\_year** part of NK **and** still allow SCD2 for mid-year changes (premium updates, deductible corrections).
* 0: plan\_id/hios\_id themselves
* 1: display name cleanup
* 2: monthly\_premium, deductible, oop\_max, coinsurance\_rate

**dim\_provider (NK: npi)**

* 0: npi
* 1: name fixups/casing
* 2: specialty, practice address, phone (providers move/change groups)

**dim\_geography / date / code sets**

* Mostly **0** (static reference).

**Mini-dim** (fast-changing member flags like high\_cost\_member, used\_app, web\_login): break them out so dim\_member doesn’t explode. Make this **Type 2** and relate by a dated bridge or by choosing the row “as of” the fact date.

**Bridge** (many-to-many): provider–plan network participation with dates (in-network vs out-of-network by period). Use this to derive network status on claims.

# 4) Effective dating + as-of joins

Use: `valid_from`, `valid_to`, `is_current` (where `valid_to = '9999-12-31'` for open).
When loading a fact, pick the right SCD2 row **as of the fact’s date**:

```sql
-- example: pick member SK as of service_date
SELECT m.member_sk
FROM dim_member m
WHERE m.member_nk = c.member_id
  AND m.valid_from <= c.service_date
  AND c.service_date < m.valid_to;
```

# 5) Change detection (how you decide to insert a new SCD2 row)

Two common ways:

* **Column-by-column compare** (simple, but verbose)
* **Hashdiff** (one hash over trimmed/normalized tracked columns; insert new row when hash changes)

Example hashdiff in staging:

```sql
SELECT
  member_id,
  encode(digest(
    concat_ws('|',
      coalesce(trim(lower(email)),''),
      coalesce(trim(lower(phone)),''),
      coalesce(trim(lower(street)),''),
      coalesce(city,''),
      coalesce(state,''),
      coalesce(zip,''),
      coalesce(region,''),
      coalesce(clinical_segment,''),
      coalesce(fpl_ratio::text,'')
    ), 'sha256'), 'hex') AS scd2_hash
FROM staging.members_raw
WHERE load_id = :load_id;
```

# 6) Dim/Facts skeletons (keep it boring and consistent)

```sql
-- dim_member
CREATE TABLE IF NOT EXISTS dw.dim_member (
  member_sk      BIGSERIAL PRIMARY KEY,
  member_nk      TEXT NOT NULL,                -- member_id
  first_name     TEXT,
  last_name      TEXT,
  dob            DATE,                         -- SCD0
  gender         CHAR(1),                      -- SCD0
  email          TEXT,                         -- SCD1
  phone          TEXT,                         -- SCD1
  street         TEXT,                         -- SCD2
  city           TEXT,                         -- SCD2
  state          CHAR(2),                      -- SCD2
  zip            TEXT,                         -- SCD2
  region         TEXT,                         -- SCD2
  fpl_ratio      NUMERIC(5,2),                 -- SCD2
  scd2_hash      TEXT,                         -- for change detection
  valid_from     DATE NOT NULL,
  valid_to       DATE NOT NULL,
  is_current     BOOLEAN NOT NULL DEFAULT TRUE
);

-- dim_plan
CREATE TABLE IF NOT EXISTS dw.dim_plan (
  plan_sk        BIGSERIAL PRIMARY KEY,
  plan_nk        TEXT NOT NULL,                -- plan_id or hios_id||csr
  effective_year INTEGER NOT NULL,
  name           TEXT,                         -- SCD1
  metal_tier     TEXT,                         -- SCD2 if mid-year changes matter
  monthly_premium NUMERIC(10,2),               -- SCD2
  deductible     INTEGER,                      -- SCD2
  oop_max        INTEGER,                      -- SCD2
  coinsurance_rate NUMERIC(5,4),               -- SCD2
  scd2_hash      TEXT,
  valid_from     DATE NOT NULL,
  valid_to       DATE NOT NULL,
  is_current     BOOLEAN NOT NULL DEFAULT TRUE
);

-- fact_claim_line (degenerate dim: claim_id stays here)
CREATE TABLE IF NOT EXISTS dw.fact_claim_line (
  claim_id        TEXT NOT NULL,               -- degenerate dimension
  service_date_sk INTEGER NOT NULL,
  member_sk       INTEGER NOT NULL,
  provider_sk     INTEGER,
  plan_sk         INTEGER,
  diagnosis_sk    INTEGER,
  procedure_sk    INTEGER,
  claim_amount    NUMERIC(12,2),
  allowed_amount  NUMERIC(12,2),
  paid_amount     NUMERIC(12,2),
  status_sk       INTEGER,
  load_id         BIGINT,
  CONSTRAINT fk_member   FOREIGN KEY(member_sk)   REFERENCES dw.dim_member(member_sk),
  CONSTRAINT fk_provider FOREIGN KEY(provider_sk) REFERENCES dw.dim_provider(provider_sk),
  CONSTRAINT fk_plan     FOREIGN KEY(plan_sk)     REFERENCES dw.dim_plan(plan_sk),
  CONSTRAINT fk_date     FOREIGN KEY(service_date_sk) REFERENCES dw.dim_date(date_sk)
);
```

Notes:

* **Degenerate dimension** = keep an ID (e.g., `claim_id`) in the fact without its own dim.
* Always add a row `-1` = “Unknown” in every dimension to survive late/missing keys.

# 7) Snapshot choices (when SCD isn’t enough)

* **Periodic snapshot (monthly)**: member counts, PMPM, premium totals. Easy trending.
* **Acc. snapshot (episode)**: enrollments from start→end with milestone dates (approved\_date, effective\_start, termination\_date).

# 8) Loading order (daily job)

1. Land to **staging** (you’ve got this).
2. Upsert **dimensions** first (resolve SCD using hashdiff).
3. Load **facts** with as-of lookups to SCD2 rows.
4. Re-key late facts (backfill) on a second pass if needed.
5. Audit counts vs `staging.load_batches`.

# 9) Where SCD3/4/6 actually show up

* **SCD3**: only when a specific report literally needs “previous\_foo” next to current. Example: store `previous_region` on `dim_member` if analysts constantly compare current vs immediately prior region.
* **SCD4**: if a dimension is massive/volatile (e.g., provider rosters with daily feeds) and you want a slim Type-1 reporting dim + a separate full history archive. Not common; weigh complexity.
* **SCD6**: you want Type-2 history **and** certain columns to behave as Type-1 on the current row (convenience for BI tools). Nice-to-have, not mandatory.

# 10) Two domain gotchas to plan for

* **Network status** (in/out): derive via provider–plan bridge effective on service\_date (don’t trust a simple flag on the claim).
* **Plan ID by year**: carriers reuse IDs; include **effective\_year** in NK or you’ll mis-join.

