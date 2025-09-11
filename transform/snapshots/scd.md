# SCD 

## basic idea
Define SCD0 scope (treat as immutable: which dims never change?)
Define SCD1 scope (overwrite-on-change: which dims can lose history?)
Define SCD2 scope (which dims get history: members? plans?)
Define SCD3 scope (track limited prior value: which single attributes need “previous_”?)
Define SCD4 scope (separate history table: any heavy-change dims needing archive split?)
Define SCD6 scope (hybrid 1+2+3: any dims needing current row + history + prior value?)
Define static snapshot facts (any mini-dims or outriggers instead of full SCD?)
Define change detection method (hash of natural-key attrs vs column-by-column)
Define effective dating columns (start_date, end_date, current_flag naming standard)

## implementation

Core conventions:
- Surrogate key: dimension_sk BIGSERIAL PRIMARY KEY
- Natural key: nk_* (e.g. member_id, plan_code)
- Hash of tracked attributes: attr_hash (SHA256 / xxhash)
- Dates: start_date DATE NOT NULL, end_date DATE, current_flag BOOLEAN NOT NULL DEFAULT true
- Audit: created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ
- All SCD logic runs inside a single transaction per batch (idempotent via staging hash)
- Late arriving dimension records: use supplied effective date; if it precedes existing start_date, insert new historical row then adjust fact foreign keys in a repair step.

Change detection (shared):
-- Staging table example: stg_member (member_id, first_name, last_name, dob, address_line1, ..., load_id)
-- Compute hash in staging (dbt model or load SQL)
SELECT
  member_id,
  first_name,
  last_name,
  dob,
  address_line1,
  encode(digest(
    concat_ws('||', coalesce(first_name,''), coalesce(last_name,''), coalesce(dob::text,''), coalesce(address_line1,'')),
    'sha256'
  ), 'hex') AS attr_hash,
  load_id
FROM stg_member;

Type 0 (SCD0 - Immutable Dimensions):
- Used for static reference data (e.g. metal tiers).
- Enforcement: On load, compare existing attr_hash; if different, log error and reject row (do NOT update).
Example validation:
SELECT s.member_id
FROM stg_member_hash s
JOIN dim_member d USING (member_id)
WHERE s.attr_hash <> d.attr_hash;
-- If any rows return, fail the batch for Type 0 dims.

Type 1 (SCD1 - Overwrite):
- Used for low-value history attributes (e.g. member email normalization).
MERGE pattern (Postgres 15+) or UPSERT emulation:
INSERT INTO dim_provider (provider_nk, name, specialty, attr_hash, updated_at)
VALUES (...)
ON CONFLICT (provider_nk) DO UPDATE
SET name = EXCLUDED.name,
    specialty = EXCLUDED.specialty,
    attr_hash = EXCLUDED.attr_hash,
    updated_at = now();
-- No history kept.

Type 2 (SCD2 - Full History):
Target dims: members (address, demographics), plans (premium, coverage), providers (network status - optional)
Steps:
1. Identify changed (hash differs) vs new vs unchanged.
WITH incoming AS (
  SELECT * FROM stg_member_hash
),
curr AS (
  SELECT * FROM dim_member WHERE current_flag
),
diff AS (
  SELECT i.*
  FROM incoming i
  LEFT JOIN curr c ON c.member_id = i.member_id
  WHERE c.member_id IS NULL                -- new
     OR c.attr_hash <> i.attr_hash         -- changed
)
-- Expire changed current rows
UPDATE dim_member d
SET end_date = CURRENT_DATE - 1,
    current_flag = false,
    updated_at = now()
FROM diff x
WHERE d.member_id = x.member_id
  AND d.current_flag
  AND d.attr_hash <> x.attr_hash;
-- Insert new current rows (new + changed)
INSERT INTO dim_member (
  member_id, first_name, last_name, dob, address_line1,
  attr_hash, start_date, end_date, current_flag
)
SELECT
  x.member_id, x.first_name, x.last_name, x.dob, x.address_line1,
  x.attr_hash, CURRENT_DATE, NULL, true
FROM diff x
LEFT JOIN curr c ON c.member_id = x.member_id
WHERE c.member_id IS NULL OR c.attr_hash <> x.attr_hash;

Type 3 (SCD3 - Previous Value Columns):
- Track limited prior value (e.g. previous_metal_tier) while overwriting current.
ALTER TABLE dim_plan ADD COLUMN previous_metal_tier TEXT;
-- Load (only when tier changes):
UPDATE dim_plan d
SET previous_metal_tier = d.metal_tier,
    metal_tier = s.metal_tier,
    attr_hash = s.attr_hash,
    updated_at = now()
FROM stg_plan_hash s
WHERE d.plan_code = s.plan_code
  AND d.metal_tier <> s.metal_tier;

Type 4 (SCD4 - History Table / Mini-Dimension):
- Current table + separate history archive for high-churn attributes (e.g. provider network affiliations).
Tables:
dim_provider (only current state)
dim_provider_history (provider_hist_sk, provider_nk, attr_set..., version_start, version_end)
Implementation:
-- On change (detected via hash):
INSERT INTO dim_provider_history (provider_nk, name, specialty, network_status, version_start, version_end)
SELECT p.provider_nk, p.name, p.specialty, p.network_status, p.start_date, CURRENT_DATE - 1
FROM dim_provider p
JOIN changed_provider c USING (provider_nk);
-- Overwrite dim_provider with new values + start_date = current_date.

Type 6 (SCD6 - 1+2+3 Hybrid):
- Keep full history rows (Type 2), plus overwrite certain non-historic attributes (Type 1), plus previous value columns (Type 3).
Approach:
- Core historical columns managed exactly like Type 2 (start/end/current_flag).
- Additional "Type 1" columns updated in-place on the current row after potential Type 2 insertion (so new row starts with latest Type1 values).
- Maintain previous_* columns only for selected attributes.
Example post Type 2 insert:
UPDATE dim_member d
SET previous_email = d.email,
    email = s.email,
    updated_at = now(),
    attr_hash = encode(digest(concat_ws('||', d.first_name, d.last_name, s.email),'sha256'),'hex')
FROM stg_member_email s
WHERE d.member_id = s.member_id
  AND d.current_flag
  AND d.email <> s.email;

Static Snapshot Facts (Periodic Snapshot):
- Capture point-in-time enrollments (e.g. monthly enrollment snapshot).
CREATE TABLE fact_enrollment_snapshot (
  snapshot_date DATE NOT NULL,
  member_sk BIGINT NOT NULL,
  plan_sk BIGINT NOT NULL,
  status TEXT,
  premium_amount NUMERIC(10,2),
  PRIMARY KEY (snapshot_date, member_sk, plan_sk)
);
-- Load monthly:
INSERT INTO fact_enrollment_snapshot (snapshot_date, member_sk, plan_sk, status, premium_amount)
SELECT DATE_TRUNC('month', CURRENT_DATE)::date AS snapshot_date,
       m.dim_member_sk,
       p.dim_plan_sk,
       e.status,
       e.premium_amount
FROM current_enrollment_view e
JOIN dim_member m ON m.member_id = e.member_id AND m.current_flag
JOIN dim_plan p   ON p.plan_code = e.plan_code AND p.current_flag
ON CONFLICT DO NOTHING;  -- idempotent for a month

Handling Late Arriving Facts:
- Facts referencing natural keys where dimension row not yet present:
  1. Insert placeholder dimension row (Type 2 start_date = fact_date, flagged is_inferred = true).
  2. When actual dimension attributes arrive, treat as Type 2 change (expire inferred row, insert full row).
  3. Update facts that pointed at inferred surrogate if a new earlier historical row must be inserted (rare; use repair script).

Surrogate Key Lookup (always current for transaction fact):
SELECT dim_member_sk
FROM dim_member
WHERE member_id = :member_id
  AND current_flag
  AND start_date <= :fact_date
  AND (end_date IS NULL OR end_date >= :fact_date);

Data Quality Checks per Load:
- Orphan expiration (no row left current_flag=true per NK): expect exactly 1 current row per NK.
SELECT member_id
FROM dim_member
GROUP BY member_id
HAVING SUM(CASE WHEN current_flag THEN 1 ELSE 0 END) <> 1;
-- Should return zero rows.

Performance Tips:
- Indexes:
  CREATE INDEX ON dim_member (member_id, current_flag);
  CREATE INDEX ON dim_member (member_id, start_date DESC);
- Partition very large Type 2 dims by start_date (monthly range partitions) if needed.

Testing Strategy:
- Unit: hash generation deterministic.
- Integration: Insert change; assert old row end_date set & new row current_flag true.
- Edge: No-op load does not mutate row count or timestamps.
