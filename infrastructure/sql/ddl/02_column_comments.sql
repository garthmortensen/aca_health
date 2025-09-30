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
-- Standard demographic columns
COMMENT ON COLUMN staging.members_raw.member_id IS 'Synthetic member identifier (MBR#####)';
COMMENT ON COLUMN staging.members_raw.first_name IS 'Member first name';
COMMENT ON COLUMN staging.members_raw.last_name IS 'Member last name';
COMMENT ON COLUMN staging.members_raw.dob IS 'Date of birth';
COMMENT ON COLUMN staging.members_raw.gender IS 'Gender code (M/F/O)';
COMMENT ON COLUMN staging.members_raw.email IS 'Member email address';
COMMENT ON COLUMN staging.members_raw.phone IS 'Member phone number';
COMMENT ON COLUMN staging.members_raw.street IS 'Member street address';
COMMENT ON COLUMN staging.members_raw.city IS 'Member city';
COMMENT ON COLUMN staging.members_raw.state IS 'Member state code';
COMMENT ON COLUMN staging.members_raw.zip IS 'Member postal code';
-- Plan and enrollment attributes
COMMENT ON COLUMN staging.members_raw.hios_id IS 'Health Insurance Oversight System identifier';
COMMENT ON COLUMN staging.members_raw.plan_network_access_type IS 'Plan network access type (HMO/PPO/EPO/etc.)';
COMMENT ON COLUMN staging.members_raw.plan_metal IS 'ACA metal tier from member enrollment';
COMMENT ON COLUMN staging.members_raw.age_group IS 'Simulated age group bucket';
COMMENT ON COLUMN staging.members_raw.region IS 'Geographic region classification';
-- Engagement and behavior metrics
COMMENT ON COLUMN staging.members_raw.call_count IS 'Number of customer service calls made';
COMMENT ON COLUMN staging.members_raw.app_login_count IS 'Number of mobile app login sessions';
COMMENT ON COLUMN staging.members_raw.web_login_count IS 'Number of web portal login sessions';
-- Risk adjustment and clinical attributes
COMMENT ON COLUMN staging.members_raw.wisconsin_area_deprivation_index IS 'Wisconsin Area Deprivation Index score';
COMMENT ON COLUMN staging.members_raw.ra_mm IS 'Risk Adjustment Member Months score';
COMMENT ON COLUMN staging.members_raw.year IS 'Data snapshot year';
-- Load metadata
COMMENT ON COLUMN staging.members_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.members_raw.load_timestamp IS 'Ingestion timestamp';
-- Enrichment attributes
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
-- Additional claims_raw columns added per objective.md
COMMENT ON COLUMN staging.claims_raw.charges IS 'Total charges amount (synonym for claim_amount)';
COMMENT ON COLUMN staging.claims_raw.allowed IS 'Allowed amount after adjudication (synonym for allowed_amount)';
COMMENT ON COLUMN staging.claims_raw.clean_claim_status IS 'Clean claim processing status indicator';
COMMENT ON COLUMN staging.claims_raw.claim_from IS 'Claim service period start date';
COMMENT ON COLUMN staging.claims_raw.clean_claim_out IS 'Clean claim processing completion date';
COMMENT ON COLUMN staging.claims_raw.utilization IS 'Service utilization metric';
COMMENT ON COLUMN staging.claims_raw.hcg_units_days IS 'Healthcare group units or service days';
COMMENT ON COLUMN staging.claims_raw.claim_type IS 'Claim type categorization (medical/pharmacy/dental/etc.)';
COMMENT ON COLUMN staging.claims_raw.major_service_category IS 'High-level service category grouping';
COMMENT ON COLUMN staging.claims_raw.provider_specialty IS 'Provider specialty from claim (may differ from provider dimension)';
COMMENT ON COLUMN staging.claims_raw.detailed_service_category IS 'Detailed service category classification';
COMMENT ON COLUMN staging.claims_raw.ms_drg IS 'Medicare Severity Diagnosis Related Group code';
COMMENT ON COLUMN staging.claims_raw.ms_drg_description IS 'MS-DRG description text';
COMMENT ON COLUMN staging.claims_raw.ms_drg_mdc IS 'Major Diagnostic Category code for MS-DRG';
COMMENT ON COLUMN staging.claims_raw.ms_drg_mdc_desc IS 'Major Diagnostic Category description';
COMMENT ON COLUMN staging.claims_raw.cpt IS 'Current Procedural Terminology code';
COMMENT ON COLUMN staging.claims_raw.cpt_consumer_description IS 'Consumer-friendly CPT code description';
COMMENT ON COLUMN staging.claims_raw.procedure_level_1 IS 'Procedure classification level 1 (broadest)';
COMMENT ON COLUMN staging.claims_raw.procedure_level_2 IS 'Procedure classification level 2';
COMMENT ON COLUMN staging.claims_raw.procedure_level_3 IS 'Procedure classification level 3';
COMMENT ON COLUMN staging.claims_raw.procedure_level_4 IS 'Procedure classification level 4';
COMMENT ON COLUMN staging.claims_raw.procedure_level_5 IS 'Procedure classification level 5 (most specific)';
COMMENT ON COLUMN staging.claims_raw.channel IS 'Distribution or service delivery channel';
COMMENT ON COLUMN staging.claims_raw.drug_name IS 'Pharmaceutical drug name (if pharmacy claim)';
COMMENT ON COLUMN staging.claims_raw.drug_class IS 'Drug therapeutic class';
COMMENT ON COLUMN staging.claims_raw.drug_subclass IS 'Drug therapeutic subclass';
COMMENT ON COLUMN staging.claims_raw.drug IS 'Generic drug identifier';
COMMENT ON COLUMN staging.claims_raw.is_oon IS '1 if out-of-network service, 0 if in-network';
COMMENT ON COLUMN staging.claims_raw.best_contracting_entity_name IS 'Primary contracting entity name';
COMMENT ON COLUMN staging.claims_raw.provider_group_name IS 'Provider group or organization name';
COMMENT ON COLUMN staging.claims_raw.ccsr_system_description IS 'Clinical Classifications Software Refined system description';
COMMENT ON COLUMN staging.claims_raw.ccsr_description IS 'CCSR category description';
COMMENT ON COLUMN staging.claims_raw.load_id IS 'FK to load_batches';
COMMENT ON COLUMN staging.claims_raw.load_timestamp IS 'Ingestion timestamp';

-- ===================== Index Comments =====================
-- Load batch indexes
COMMENT ON INDEX staging.uq_load_batches_file_pattern_completed IS 'Ensures only one completed batch per file pattern for idempotent loads';

-- Raw table load tracking indexes
COMMENT ON INDEX staging.idx_plans_raw_load IS 'Performance index for load batch queries on plans';
COMMENT ON INDEX staging.idx_providers_raw_load IS 'Performance index for load batch queries on providers';
COMMENT ON INDEX staging.idx_members_raw_load IS 'Performance index for load batch queries on members';
COMMENT ON INDEX staging.idx_enrollments_raw_load IS 'Performance index for load batch queries on enrollments';
COMMENT ON INDEX staging.idx_claims_raw_load IS 'Performance index for load batch queries on claims';

-- Claims raw business indexes
COMMENT ON INDEX staging.idx_claims_raw_member IS 'Performance index for member-based claims queries';
COMMENT ON INDEX staging.idx_claims_raw_provider IS 'Performance index for provider-based claims queries';
COMMENT ON INDEX staging.idx_claims_raw_plan IS 'Performance index for plan-based claims queries';
COMMENT ON INDEX staging.idx_claims_raw_service_date IS 'Performance index for time-based claims queries';
