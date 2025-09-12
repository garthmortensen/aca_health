-- Load fact tables (idempotent: anti-join on natural key PKs)
BEGIN;

-- fact_claim
INSERT INTO dw.fact_claim (
    claim_id, member_sk, provider_sk, plan_sk, date_key, service_date,
    claim_amount, allowed_amount, paid_amount, status,
    diagnosis_code, procedure_code, load_id
)
SELECT
    c.claim_id,
    dm.member_sk,
    dp.provider_sk,
    pl.plan_sk,
    (
        EXTRACT(YEAR FROM c.service_date)::int * 10000
        + EXTRACT(MONTH FROM c.service_date)::int * 100
        + EXTRACT(DAY FROM c.service_date)::int
    ) AS date_key,
    c.service_date,
    c.claim_amount,
    c.allowed_amount,
    c.paid_amount,
    c.status,
    c.diagnosis_code,
    c.procedure_code,
    c.load_id
FROM staging.claims_raw AS c
INNER JOIN dw.dim_member AS dm ON c.member_id = dm.member_id AND dm.current_flag
INNER JOIN
    dw.dim_provider AS dp
    ON c.provider_id = dp.provider_id AND dp.current_flag
INNER JOIN
    dw.dim_plan AS pl
    ON
        c.plan_id = pl.plan_id
        AND pl.effective_year = EXTRACT(YEAR FROM c.service_date)
        AND pl.current_flag
LEFT JOIN dw.fact_claim AS fc ON c.claim_id = fc.claim_id
WHERE fc.claim_id IS NULL;

-- fact_enrollment
INSERT INTO dw.fact_enrollment (
    enrollment_id, member_sk, plan_sk, start_date_key, end_date_key,
    start_date, end_date, premium_paid, csr_variant, coverage_days, load_id
)
SELECT
    e.enrollment_id,
    dm.member_sk,
    pl.plan_sk,
    (
        EXTRACT(YEAR FROM e.start_date)::int * 10000
        + EXTRACT(MONTH FROM e.start_date)::int * 100
        + EXTRACT(DAY FROM e.start_date)::int
    ) AS start_date_key,
    (
        EXTRACT(YEAR FROM e.end_date)::int * 10000
        + EXTRACT(MONTH FROM e.end_date)::int * 100
        + EXTRACT(DAY FROM e.end_date)::int
    ) AS end_date_key,
    e.start_date,
    e.end_date,
    e.premium_paid,
    e.csr_variant,
    (e.end_date - e.start_date + 1)::int AS coverage_days,
    e.load_id
FROM staging.enrollments_raw AS e
INNER JOIN dw.dim_member AS dm ON e.member_id = dm.member_id AND dm.current_flag
INNER JOIN
    dw.dim_plan AS pl
    ON
        e.plan_id = pl.plan_id
        AND pl.effective_year = EXTRACT(YEAR FROM e.start_date)
        AND pl.current_flag
LEFT JOIN dw.fact_enrollment AS fe ON e.enrollment_id = fe.enrollment_id
WHERE fe.enrollment_id IS NULL;

COMMIT;
