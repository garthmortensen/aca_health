-- Load fact tables (idempotent: anti-join on natural key PKs)
BEGIN;

-- fact_claim
INSERT INTO dw.fact_claim (
  claim_id, member_sk, provider_sk, plan_sk, date_key, service_date,
  claim_amount, allowed_amount, paid_amount, status,
  diagnosis_code, procedure_code, load_id
)
SELECT c.claim_id,
       dm.member_sk,
       dp.provider_sk,
       pl.plan_sk,
       (EXTRACT(YEAR FROM c.service_date)::int*10000 + EXTRACT(MONTH FROM c.service_date)::int*100 + EXTRACT(DAY FROM c.service_date)::int) AS date_key,
       c.service_date,
       c.claim_amount, c.allowed_amount, c.paid_amount, c.status,
       c.diagnosis_code, c.procedure_code, c.load_id
FROM staging.claims_raw c
JOIN dw.dim_member dm   ON dm.member_id = c.member_id AND dm.current_flag
JOIN dw.dim_provider dp ON dp.provider_id = c.provider_id AND dp.current_flag
JOIN dw.dim_plan pl     ON pl.plan_id = c.plan_id AND pl.effective_year = EXTRACT(YEAR FROM c.service_date) AND pl.current_flag
LEFT JOIN dw.fact_claim fc ON fc.claim_id = c.claim_id
WHERE fc.claim_id IS NULL;

-- fact_enrollment
INSERT INTO dw.fact_enrollment (
  enrollment_id, member_sk, plan_sk, start_date_key, end_date_key,
  start_date, end_date, premium_paid, csr_variant, coverage_days, load_id
)
SELECT e.enrollment_id,
       dm.member_sk,
       pl.plan_sk,
       (EXTRACT(YEAR FROM e.start_date)::int*10000 + EXTRACT(MONTH FROM e.start_date)::int*100 + EXTRACT(DAY FROM e.start_date)::int) AS start_date_key,
       (EXTRACT(YEAR FROM e.end_date)::int*10000 + EXTRACT(MONTH FROM e.end_date)::int*100 + EXTRACT(DAY FROM e.end_date)::int) AS end_date_key,
       e.start_date,
       e.end_date,
       e.premium_paid,
       e.csr_variant,
       (e.end_date - e.start_date + 1)::int AS coverage_days,
       e.load_id
FROM staging.enrollments_raw e
JOIN dw.dim_member dm ON dm.member_id = e.member_id AND dm.current_flag
JOIN dw.dim_plan pl   ON pl.plan_id = e.plan_id AND pl.effective_year = EXTRACT(YEAR FROM e.start_date) AND pl.current_flag
LEFT JOIN dw.fact_enrollment fe ON fe.enrollment_id = e.enrollment_id
WHERE fe.enrollment_id IS NULL;

COMMIT;
