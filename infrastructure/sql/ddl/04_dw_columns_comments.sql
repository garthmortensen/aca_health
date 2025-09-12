-- Documentation comments for dw (data warehouse) schema objects
-- Separated from structural DDL for clarity & idempotent re-runs.

-- Schema
COMMENT ON SCHEMA dw IS 'Core dimensional and fact schema (star model)';

-- Sequences (explicit)
COMMENT ON SEQUENCE dw.sk_member_seq IS 'Surrogate key generator for dim_member rows (SCD2 versions)';
COMMENT ON SEQUENCE dw.sk_provider_seq IS 'Surrogate key generator for dim_provider rows (SCD2 versions)';
COMMENT ON SEQUENCE dw.sk_plan_seq IS 'Surrogate key generator for dim_plan rows (SCD2 versions)';
COMMENT ON SEQUENCE dw.sk_date_seq IS 'Reserved sequence (normally date dimension uses natural key)';

-- ===================== dim_date =====================
COMMENT ON TABLE dw.dim_date IS 'Date dimension (one row per calendar day; static range)';
COMMENT ON COLUMN dw.dim_date.date_key IS 'YYYYMMDD integer surrogate/natural key (e.g., 20250131)';
COMMENT ON COLUMN dw.dim_date.full_date IS 'Actual date value';
COMMENT ON COLUMN dw.dim_date.year IS '4-digit calendar year';
COMMENT ON COLUMN dw.dim_date.quarter IS 'Calendar quarter number (1-4)';
COMMENT ON COLUMN dw.dim_date.month IS 'Month number (1-12)';
COMMENT ON COLUMN dw.dim_date.month_name IS 'Full month name';
COMMENT ON COLUMN dw.dim_date.day IS 'Day of month (1-31)';
COMMENT ON COLUMN dw.dim_date.day_of_week IS 'ISO day of week (1=Mon .. 7=Sun)';
COMMENT ON COLUMN dw.dim_date.day_name IS 'Weekday name';
COMMENT ON COLUMN dw.dim_date.week_of_year IS 'ISO week number (1-53)';
COMMENT ON COLUMN dw.dim_date.is_weekend IS 'TRUE if Saturday/Sunday';
COMMENT ON COLUMN dw.dim_date.created_at IS 'Row creation timestamp';

-- ===================== dim_member (SCD2) =====================
COMMENT ON TABLE dw.dim_member IS 'Member dimension (SCD2) with demographic & engagement attributes';
COMMENT ON COLUMN dw.dim_member.member_sk IS 'Surrogate key identifying a specific historical version';
COMMENT ON COLUMN dw.dim_member.member_id IS 'Natural business member identifier from source';
COMMENT ON COLUMN dw.dim_member.first_name IS 'Member first name';
COMMENT ON COLUMN dw.dim_member.last_name IS 'Member last name';
COMMENT ON COLUMN dw.dim_member.dob IS 'Date of birth';
COMMENT ON COLUMN dw.dim_member.gender IS 'Gender code';
COMMENT ON COLUMN dw.dim_member.email IS 'Email address';
COMMENT ON COLUMN dw.dim_member.phone IS 'Phone number';
COMMENT ON COLUMN dw.dim_member.street IS 'Street address';
COMMENT ON COLUMN dw.dim_member.city IS 'City';
COMMENT ON COLUMN dw.dim_member.state IS 'State/region code';
COMMENT ON COLUMN dw.dim_member.zip IS 'Postal code';
COMMENT ON COLUMN dw.dim_member.federal_poverty_level_ratio IS 'Income divided by Federal Poverty Level (ratio)';
COMMENT ON COLUMN dw.dim_member.plan_network_access_type IS 'Network access type descriptor';
COMMENT ON COLUMN dw.dim_member.plan_metal IS 'Plan metal tier (Bronze/Silver/Gold/etc.) snapshot';
COMMENT ON COLUMN dw.dim_member.age_group IS 'Pre-bucketed simulated age group';
COMMENT ON COLUMN dw.dim_member.region IS 'Internal regional grouping';
COMMENT ON COLUMN dw.dim_member.enrollment_length_continuous IS 'Approx continuous months enrolled in current year';
COMMENT ON COLUMN dw.dim_member.clinical_segment IS 'Clinical segment classification';
COMMENT ON COLUMN dw.dim_member.general_agency_name IS 'General agency (distribution channel) name';
COMMENT ON COLUMN dw.dim_member.broker_name IS 'Broker name';
COMMENT ON COLUMN dw.dim_member.sa_contracting_entity_name IS 'Contracting entity';
COMMENT ON COLUMN dw.dim_member.new_member_in_period IS '1 if first year member';
COMMENT ON COLUMN dw.dim_member.member_used_app IS '1 if mobile app used';
COMMENT ON COLUMN dw.dim_member.member_had_web_login IS '1 if any web portal login';
COMMENT ON COLUMN dw.dim_member.member_visited_new_provider_ind IS '1 if member visited a new provider';
COMMENT ON COLUMN dw.dim_member.high_cost_member IS '1 if simulated high cost classification';
COMMENT ON COLUMN dw.dim_member.mutually_exclusive_hcc_condition IS 'Chosen chronic condition bucket';
COMMENT ON COLUMN dw.dim_member.geographic_reporting IS 'Geographic reporting code';
COMMENT ON COLUMN dw.dim_member.year IS 'Snapshot / attribution year (source)';
COMMENT ON COLUMN dw.dim_member.validity_start_ts IS 'SCD2 version start timestamp (inclusive)';
COMMENT ON COLUMN dw.dim_member.validity_end_ts IS 'SCD2 version end timestamp (exclusive boundary sentinel if 9999-12-31)';
COMMENT ON COLUMN dw.dim_member.current_flag IS 'TRUE if current active version';
COMMENT ON COLUMN dw.dim_member.attr_hash IS 'SHA256 hash of normalized business attributes for change detection';
COMMENT ON COLUMN dw.dim_member.load_id IS 'Staging load_batches.load_id that produced this row';
COMMENT ON COLUMN dw.dim_member.created_at IS 'Row insertion timestamp';

-- ===================== dim_provider (SCD2) =====================
COMMENT ON TABLE dw.dim_provider IS 'Provider dimension (SCD2)';
COMMENT ON COLUMN dw.dim_provider.provider_sk IS 'Surrogate key (version identifier)';
COMMENT ON COLUMN dw.dim_provider.provider_id IS 'Natural provider identifier';
COMMENT ON COLUMN dw.dim_provider.npi IS 'Simulated NPI-like identifier';
COMMENT ON COLUMN dw.dim_provider.name IS 'Provider full name';
COMMENT ON COLUMN dw.dim_provider.specialty IS 'Medical specialty';
COMMENT ON COLUMN dw.dim_provider.street IS 'Street address';
COMMENT ON COLUMN dw.dim_provider.city IS 'City';
COMMENT ON COLUMN dw.dim_provider.state IS 'State code';
COMMENT ON COLUMN dw.dim_provider.zip IS 'Postal code';
COMMENT ON COLUMN dw.dim_provider.phone IS 'Phone number';
COMMENT ON COLUMN dw.dim_provider.validity_start_ts IS 'SCD2 version start timestamp';
COMMENT ON COLUMN dw.dim_provider.validity_end_ts IS 'SCD2 version end timestamp';
COMMENT ON COLUMN dw.dim_provider.current_flag IS 'TRUE if current version';
COMMENT ON COLUMN dw.dim_provider.attr_hash IS 'Hash of change tracked attributes';
COMMENT ON COLUMN dw.dim_provider.load_id IS 'Originating load batch id';
COMMENT ON COLUMN dw.dim_provider.created_at IS 'Row insertion timestamp';

-- ===================== dim_plan (SCD2) =====================
COMMENT ON TABLE dw.dim_plan IS 'Plan dimension (SCD2) - natural key (plan_id, effective_year)';
COMMENT ON COLUMN dw.dim_plan.plan_sk IS 'Surrogate key (version identifier)';
COMMENT ON COLUMN dw.dim_plan.plan_id IS 'Plan identifier from source';
COMMENT ON COLUMN dw.dim_plan.name IS 'Plan marketing name';
COMMENT ON COLUMN dw.dim_plan.metal_tier IS 'ACA metal tier';
COMMENT ON COLUMN dw.dim_plan.monthly_premium IS 'Monthly premium amount';
COMMENT ON COLUMN dw.dim_plan.deductible IS 'Annual deductible';
COMMENT ON COLUMN dw.dim_plan.oop_max IS 'Out-of-pocket maximum';
COMMENT ON COLUMN dw.dim_plan.coinsurance_rate IS 'Member coinsurance fraction (0-1)';
COMMENT ON COLUMN dw.dim_plan.pcp_copay IS 'Primary care copay';
COMMENT ON COLUMN dw.dim_plan.effective_year IS 'Effective year (component of natural key)';
COMMENT ON COLUMN dw.dim_plan.validity_start_ts IS 'SCD2 version start timestamp';
COMMENT ON COLUMN dw.dim_plan.validity_end_ts IS 'SCD2 version end timestamp';
COMMENT ON COLUMN dw.dim_plan.current_flag IS 'TRUE if current version';
COMMENT ON COLUMN dw.dim_plan.attr_hash IS 'Hash of change tracked attributes';
COMMENT ON COLUMN dw.dim_plan.load_id IS 'Originating load batch id';
COMMENT ON COLUMN dw.dim_plan.created_at IS 'Row insertion timestamp';

-- ===================== fact_claim =====================
COMMENT ON TABLE dw.fact_claim IS 'Claim fact table (one row per claim_id)';
COMMENT ON COLUMN dw.fact_claim.claim_id IS 'Degenerate natural identifier of claim';
COMMENT ON COLUMN dw.fact_claim.member_sk IS 'FK to dim_member (surrogate key)';
COMMENT ON COLUMN dw.fact_claim.provider_sk IS 'FK to dim_provider';
COMMENT ON COLUMN dw.fact_claim.plan_sk IS 'FK to dim_plan';
COMMENT ON COLUMN dw.fact_claim.date_key IS 'FK to dim_date (service date)';
COMMENT ON COLUMN dw.fact_claim.service_date IS 'Date of service';
COMMENT ON COLUMN dw.fact_claim.claim_amount IS 'Billed claim amount';
COMMENT ON COLUMN dw.fact_claim.allowed_amount IS 'Allowed amount after adjudication';
COMMENT ON COLUMN dw.fact_claim.paid_amount IS 'Paid amount';
COMMENT ON COLUMN dw.fact_claim.status IS 'Claim status (approved/denied/pending)';
COMMENT ON COLUMN dw.fact_claim.diagnosis_code IS 'Primary diagnosis code';
COMMENT ON COLUMN dw.fact_claim.procedure_code IS 'Procedure code';
COMMENT ON COLUMN dw.fact_claim.load_id IS 'Staging load batch id source';
COMMENT ON COLUMN dw.fact_claim.created_at IS 'Insertion timestamp';

-- ===================== fact_enrollment =====================
COMMENT ON TABLE dw.fact_enrollment IS 'Enrollment fact (continuous member-plan coverage periods)';
COMMENT ON COLUMN dw.fact_enrollment.enrollment_id IS 'Natural identifier of enrollment period';
COMMENT ON COLUMN dw.fact_enrollment.member_sk IS 'FK to dim_member';
COMMENT ON COLUMN dw.fact_enrollment.plan_sk IS 'FK to dim_plan';
COMMENT ON COLUMN dw.fact_enrollment.start_date_key IS 'FK to dim_date for coverage start';
COMMENT ON COLUMN dw.fact_enrollment.end_date_key IS 'FK to dim_date for coverage end';
COMMENT ON COLUMN dw.fact_enrollment.start_date IS 'Coverage start date';
COMMENT ON COLUMN dw.fact_enrollment.end_date IS 'Coverage end date';
COMMENT ON COLUMN dw.fact_enrollment.premium_paid IS 'Premium paid by member for period';
COMMENT ON COLUMN dw.fact_enrollment.csr_variant IS 'Cost sharing reduction variant';
COMMENT ON COLUMN dw.fact_enrollment.coverage_days IS 'Number of covered days (derived)';
COMMENT ON COLUMN dw.fact_enrollment.load_id IS 'Staging load batch id source';
COMMENT ON COLUMN dw.fact_enrollment.created_at IS 'Insertion timestamp';

-- ===================== Helper Views =====================
COMMENT ON VIEW dw.v_dim_member_current IS 'Convenience view of current (active) member dimension versions';
COMMENT ON VIEW dw.v_dim_provider_current IS 'Convenience view of current provider dimension versions';
COMMENT ON VIEW dw.v_dim_plan_current IS 'Convenience view of current plan dimension versions';
