-- SCD2 load for dim_member, dim_provider, dim_plan.
-- Assumes staging tables freshly loaded.
-- Wrap in a transaction for atomicity when run manually.

BEGIN;

-- ================= dim_member =================
WITH src AS (
    SELECT
        m.*,
        m.load_id
    FROM staging.members_raw AS m
),

candidate AS (
    SELECT
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
        federal_poverty_level_ratio,
        plan_network_access_type,
        plan_metal,
        age_group,
        region,
        enrollment_length_continuous,
        clinical_segment,
        general_agency_name,
        broker_name,
        sa_contracting_entity_name,
        new_member_in_period,
        member_used_app,
        member_had_web_login,
        member_visited_new_provider_ind,
        high_cost_member,
        mutually_exclusive_hcc_condition,
        geographic_reporting,
        year,
        load_id,
        encode(digest(concat_ws(
            '||',
            coalesce(member_id, ''),
            coalesce(first_name, ''),
            coalesce(last_name, ''),
            to_char(dob, 'YYYY-MM-DD'),
            coalesce(gender, ''),
            coalesce(email, ''),
            coalesce(phone, ''),
            coalesce(street, ''),
            coalesce(city, ''),
            coalesce(state, ''),
            coalesce(zip, ''),
            coalesce(federal_poverty_level_ratio::text, ''),
            coalesce(plan_network_access_type, ''),
            coalesce(plan_metal, ''),
            coalesce(age_group, ''),
            coalesce(region, ''),
            coalesce(enrollment_length_continuous::text, ''),
            coalesce(clinical_segment, ''),
            coalesce(general_agency_name, ''),
            coalesce(broker_name, ''),
            coalesce(sa_contracting_entity_name, ''),
            coalesce(new_member_in_period::text, ''),
            coalesce(member_used_app::text, ''),
            coalesce(member_had_web_login::text, ''),
            coalesce(member_visited_new_provider_ind::text, ''),
            coalesce(high_cost_member::text, ''),
            coalesce(mutually_exclusive_hcc_condition, ''),
            coalesce(geographic_reporting, ''), coalesce(year::text, '')
        ), 'sha256'), 'hex') AS attr_hash
    FROM src
),

changes AS (
    SELECT c.*
    FROM candidate AS c
    LEFT JOIN dw.dim_member AS cur
        ON c.member_id = cur.member_id AND cur.current_flag
    WHERE cur.member_id IS NULL OR cur.attr_hash <> c.attr_hash
),

expired AS (
    UPDATE dw.dim_member dm
    SET validity_end_ts = now(), current_flag = FALSE
    FROM changes AS ch
    WHERE dm.member_id = ch.member_id AND dm.current_flag
    RETURNING dm.member_id
)

INSERT INTO dw.dim_member (
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
    federal_poverty_level_ratio,
    plan_network_access_type,
    plan_metal,
    age_group,
    region,
    enrollment_length_continuous,
    clinical_segment,
    general_agency_name,
    broker_name,
    sa_contracting_entity_name,
    new_member_in_period,
    member_used_app,
    member_had_web_login,
    member_visited_new_provider_ind,
    high_cost_member,
    mutually_exclusive_hcc_condition,
    geographic_reporting, year, attr_hash, load_id
)
SELECT
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
    federal_poverty_level_ratio,
    plan_network_access_type,
    plan_metal,
    age_group,
    region,
    enrollment_length_continuous,
    clinical_segment,
    general_agency_name,
    broker_name,
    sa_contracting_entity_name,
    new_member_in_period,
    member_used_app,
    member_had_web_login,
    member_visited_new_provider_ind,
    high_cost_member,
    mutually_exclusive_hcc_condition,
    geographic_reporting,
    year,
    attr_hash,
    load_id
FROM changes;

-- ================= dim_provider =================
WITH src AS (
    SELECT
        p.*,
        p.load_id
    FROM staging.providers_raw AS p
),

candidate AS (
    SELECT
        provider_id,
        npi,
        name,
        specialty,
        street,
        city,
        state,
        zip,
        phone,
        load_id,
        encode(digest(concat_ws(
            '||',
            coalesce(provider_id, ''),
            coalesce(npi, ''),
            coalesce(name, ''),
            coalesce(specialty, ''),
            coalesce(street, ''),
            coalesce(city, ''),
            coalesce(state, ''),
            coalesce(zip, ''),
            coalesce(phone, '')
        ), 'sha256'), 'hex') AS attr_hash
    FROM src
),

changes AS (
    SELECT c.*
    FROM candidate AS c
    LEFT JOIN dw.dim_provider AS cur
        ON c.provider_id = cur.provider_id AND cur.current_flag
    WHERE cur.provider_id IS NULL OR cur.attr_hash <> c.attr_hash
),

expired AS (
    UPDATE dw.dim_provider dp
    SET validity_end_ts = now(), current_flag = FALSE
    FROM changes AS ch
    WHERE dp.provider_id = ch.provider_id AND dp.current_flag
    RETURNING dp.provider_id
)

INSERT INTO dw.dim_provider (
    provider_id,
    npi,
    name,
    specialty,
    street,
    city,
    state,
    zip,
    phone,
    attr_hash,
    load_id
)
SELECT
    provider_id,
    npi,
    name,
    specialty,
    street,
    city,
    state,
    zip,
    phone,
    attr_hash,
    load_id
FROM changes;

-- ================= dim_plan =================
WITH src AS (
    SELECT
        pl.*,
        pl.load_id
    FROM staging.plans_raw AS pl
),

candidate AS (
    SELECT
        plan_id,
        name,
        metal_tier,
        monthly_premium,
        deductible,
        oop_max,
        coinsurance_rate,
        pcp_copay,
        effective_year,
        load_id,
        encode(digest(concat_ws(
            '||',
            coalesce(plan_id, ''), coalesce(name, ''), coalesce(metal_tier, ''),
            coalesce(monthly_premium::text, ''),
            coalesce(deductible::text, ''),
            coalesce(oop_max::text, ''),
            coalesce(coinsurance_rate::text, ''),
            coalesce(pcp_copay::text, ''),
            coalesce(effective_year::text, '')
        ), 'sha256'), 'hex') AS attr_hash
    FROM src
),

changes AS (
    SELECT c.*
    FROM candidate AS c
    LEFT JOIN dw.dim_plan AS cur
        ON
            c.plan_id = cur.plan_id
            AND c.effective_year = cur.effective_year
            AND cur.current_flag
    WHERE cur.plan_id IS NULL OR cur.attr_hash <> c.attr_hash
),

expired AS (
    UPDATE dw.dim_plan dp
    SET validity_end_ts = now(), current_flag = FALSE
    FROM changes AS ch
    WHERE
        dp.plan_id = ch.plan_id
        AND dp.effective_year = ch.effective_year
        AND dp.current_flag
    RETURNING dp.plan_id
)

INSERT INTO dw.dim_plan (
    plan_id,
    name,
    metal_tier,
    monthly_premium,
    deductible,
    oop_max,
    coinsurance_rate,
    pcp_copay,
    effective_year,
    attr_hash,
    load_id
)
SELECT
    plan_id,
    name,
    metal_tier,
    monthly_premium,
    deductible,
    oop_max,
    coinsurance_rate,
    pcp_copay,
    effective_year,
    attr_hash,
    load_id
FROM changes;

COMMIT;
