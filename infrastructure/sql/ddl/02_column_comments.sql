-- Documentation comments for staging schema (separated from DDL)

COMMENT ON TABLE staging.load_batches IS 'Load batch metadata for raw file ingests';
COMMENT ON COLUMN staging.load_batches.source_name IS 'Origin system or generator name';
COMMENT ON COLUMN staging.load_batches.description IS 'Free-form load description';
COMMENT ON COLUMN staging.load_batches.file_pattern IS 'Loaded file name or glob pattern';
COMMENT ON COLUMN staging.load_batches.started_at IS 'Batch start timestamp';
COMMENT ON COLUMN staging.load_batches.completed_at IS 'Batch completion timestamp';
COMMENT ON COLUMN staging.load_batches.row_count IS 'Rows ingested for this load';
COMMENT ON COLUMN staging.load_batches.status IS 'started | completed | failed';
COMMENT ON COLUMN staging.load_batches.load_id IS 'Surrogate primary key for load batch';

COMMENT ON TABLE staging.plans_raw IS 'Raw plan seed data (one row per synthetic plan)';
COMMENT ON COLUMN staging.plans_raw.plan_id IS 'Synthetic plan identifier (PLN####)';
COMMENT ON COLUMN staging.plans_raw.name IS 'Plan marketing name';
COMMENT ON COLUMN staging.plans_raw.metal_tier IS 'ACA metal tier Bronze/Silver/Gold/Platinum';
COMMENT ON COLUMN staging.plans_raw.monthly_premium IS 'Monthly premium amount';
COMMENT ON COLUMN staging.plans_raw.deductible IS 'Annual deductible';
COMMENT ON COLUMN staging.plans_raw.oop_max IS 'Out-of-pocket maximum';
COMMENT ON COLUMN staging.plans_raw.coinsurance_rate IS 'Member coinsurance fraction (0-1)';
COMMENT ON COLUMN staging.plans_raw.pcp_copay IS 'Primary care visit copay';
COMMENT ON COLUMN staging.plans_raw.effective_year IS 'Plan effective year';
COMMENT ON COLUMN staging.plans_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.plans_raw.load_timestamp IS 'Ingestion timestamp';

COMMENT ON TABLE staging.providers_raw IS 'Raw provider seed data';
COMMENT ON COLUMN staging.providers_raw.provider_id IS 'Synthetic provider id (PRV#####)';
COMMENT ON COLUMN staging.providers_raw.npi IS 'Fake NPI-like number';
COMMENT ON COLUMN staging.providers_raw.name IS 'Provider full name';
COMMENT ON COLUMN staging.providers_raw.specialty IS 'Medical specialty';
COMMENT ON COLUMN staging.providers_raw.street IS 'Street address';
COMMENT ON COLUMN staging.providers_raw.city IS 'City';
COMMENT ON COLUMN staging.providers_raw.state IS 'State code';
COMMENT ON COLUMN staging.providers_raw.zip IS 'Postal code';
COMMENT ON COLUMN staging.providers_raw.phone IS 'Contact phone number';
COMMENT ON COLUMN staging.providers_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.providers_raw.load_timestamp IS 'Ingestion timestamp';

COMMENT ON TABLE staging.members_raw IS 'Raw member seed data with enrichment attributes';
COMMENT ON COLUMN staging.members_raw.fpl_ratio IS 'Income / Federal Poverty Level ratio';
COMMENT ON COLUMN staging.members_raw.enrollment_length_continuous IS 'Approx continuous enrollment months within year';
COMMENT ON COLUMN staging.members_raw.new_member_in_period IS '1 if first year member';
COMMENT ON COLUMN staging.members_raw.member_used_app IS '1 if member used mobile app';
COMMENT ON COLUMN staging.members_raw.member_had_web_login IS '1 if member logged into web portal';
COMMENT ON COLUMN staging.members_raw.member_visited_new_provider_ind IS '1 if member visited a new provider';
COMMENT ON COLUMN staging.members_raw.high_cost_member IS '1 if simulated high cost member';
COMMENT ON COLUMN staging.members_raw.mutually_exclusive_hcc_condition IS 'One chosen chronic condition bucket (simulated)';

COMMENT ON TABLE staging.enrollments_raw IS 'Raw enrollment period snapshots';
COMMENT ON COLUMN staging.enrollments_raw.enrollment_id IS 'Synthetic enrollment identifier';
COMMENT ON COLUMN staging.enrollments_raw.member_id IS 'Member identifier (not FK constrained)';
COMMENT ON COLUMN staging.enrollments_raw.plan_id IS 'Plan identifier (not FK constrained)';
COMMENT ON COLUMN staging.enrollments_raw.start_date IS 'Coverage start date';
COMMENT ON COLUMN staging.enrollments_raw.end_date IS 'Coverage end date (capped to year)';
COMMENT ON COLUMN staging.enrollments_raw.premium_paid IS 'Premium paid by member';
COMMENT ON COLUMN staging.enrollments_raw.csr_variant IS 'Cost-sharing reduction variant code';
COMMENT ON COLUMN staging.enrollments_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.enrollments_raw.load_timestamp IS 'Ingestion timestamp';

COMMENT ON TABLE staging.claims_raw IS 'Raw medical claims (ICD-11 diagnosis, CPT procedure sample codes)';
COMMENT ON COLUMN staging.claims_raw.claim_id IS 'Synthetic claim identifier';
COMMENT ON COLUMN staging.claims_raw.member_id IS 'Member identifier (not FK constrained)';
COMMENT ON COLUMN staging.claims_raw.provider_id IS 'Provider identifier (not FK constrained)';
COMMENT ON COLUMN staging.claims_raw.plan_id IS 'Plan identifier (snapshot at claim)';
COMMENT ON COLUMN staging.claims_raw.service_date IS 'Date of service';
COMMENT ON COLUMN staging.claims_raw.claim_amount IS 'Billed claim amount';
COMMENT ON COLUMN staging.claims_raw.allowed_amount IS 'Allowed amount after adjudication';
COMMENT ON COLUMN staging.claims_raw.paid_amount IS 'Paid amount (0 if denied/pending)';
COMMENT ON COLUMN staging.claims_raw.status IS 'Claim status approved/denied/pending';
COMMENT ON COLUMN staging.claims_raw.diagnosis_code IS 'ICD-11 diagnosis code (sample set)';
COMMENT ON COLUMN staging.claims_raw.procedure_code IS 'CPT procedure code (sample set)';
COMMENT ON COLUMN staging.claims_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.claims_raw.load_timestamp IS 'Ingestion timestamp';
