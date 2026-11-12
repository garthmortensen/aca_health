{{ config(materialized='view', schema='dw') }}
-- Drug dimension keyed by NDC. Carries tier, prior authorization requirement, and the policy
-- that governs the prior authorization so pharmacy facts can be sliced by benefit design.

select
    ndc,
    drug_name,
    generic_name,
    brand_name,
    drug_class,
    drug_subclass,
    is_generic,
    is_specialty,
    formulary_tier,
    requires_prior_authorization,
    prior_authorization_policy_id,
    quantity_limit_per_fill,
    standard_days_supply,
    wac_per_fill_low,
    wac_per_fill_high,
    case
        when drug_subclass = 'GLP-1 Receptor Agonists' then 'GLP-1'
        when is_specialty = 1 then 'Specialty'
        when is_generic = 1 then 'Generic'
        else 'Brand'
    end as cost_category
from {{ ref('stg_formulary') }}
