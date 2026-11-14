"""The deterministic layer: look up each policy fact in the warehouse. No AI.

For one request this returns {fact: {"value": ..., "evidence": ...}}. A value of
None means the warehouse cannot say, which is different from "no".

  drug_on_policy_list            the request's drug name against the policy's drug list
  age                            dim_member.date_of_birth as of the request date
  has_type2_diabetes_diagnosis   an E11 diagnosis on a medical claim. Claims can confirm
                                 the diagnosis but not rule it out, so no claim = None
  hba1c_percent                  the value submitted on the request. The warehouse has
                                 no lab results table, so this is the closest thing
  prior_therapy_days             days supply of paid metformin fills before the request

Usage:
  python -m pbm.warehouse PA2022000023     # print the facts for one request
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))
POLICY, SETTINGS = CONFIG["policy"], CONFIG["warehouse"]

SQL = """
select r.prior_authorization_request_id as request_id,
       r.drug_name, r.request_date, r.hba1c_percent, r.hba1c_date,
       m.date_of_birth,
       dx.codes as diabetes_codes, dx.claims as diabetes_claims,
       rx.days as prior_therapy_days, rx.fills as prior_therapy_fills, rx.first_fill
from dw.fct_prior_authorization_request r
left join dw.dim_member m using (member_id)
left join lateral (
    select string_agg(distinct c.diagnosis_code, ', ') as codes, count(*) as claims
    from dw.fct_claim c
    where c.member_id = r.member_id and c.diagnosis_code like $diagnosis and c.claim_date <= r.request_date
) dx on true
left join lateral (
    select coalesce(sum(p.days_supply), 0) as days, count(*) as fills, min(p.fill_date) as first_fill
    from dw.fct_pharmacy_claim p
    where p.member_id = r.member_id and p.is_paid and p.generic_name ilike $drug and p.fill_date < r.request_date
) rx on true
where list_contains($ids, r.prior_authorization_request_id)
"""


def age_on(date_of_birth: date, on: date) -> int:
    """Whole years between a date of birth and a date."""
    return on.year - date_of_birth.year - ((on.month, on.day) < (date_of_birth.month, date_of_birth.day))


def facts(row: dict) -> dict:
    """One warehouse row -> {fact: {"value", "evidence"}}."""
    drug = SETTINGS["prior_therapy_drug"]
    out = {}

    on_list = any(row["drug_name"].lower().startswith(d.lower()) for d in POLICY["drugs"])
    out["drug_on_policy_list"] = {
        "value": on_list,
        "evidence": f"Requested drug: {row['drug_name']}. Policy covers: {', '.join(POLICY['drugs'])}"}

    if row["date_of_birth"]:
        out["age"] = {
            "value": age_on(row["date_of_birth"], row["request_date"]),
            "evidence": f"Date of birth {row['date_of_birth']} on file, request dated {row['request_date']}"}
    else:
        out["age"] = {"value": None, "evidence": "No date of birth on file"}

    if row["diabetes_claims"]:
        out["has_type2_diabetes_diagnosis"] = {
            "value": True,
            "evidence": f"{row['diabetes_claims']} medical claim(s) with diagnosis {row['diabetes_codes']}"}
    else:
        out["has_type2_diabetes_diagnosis"] = {
            "value": None,
            "evidence": f"No medical claim with a {SETTINGS['diabetes_diagnosis_code_prefix']} diagnosis"}

    if row["hba1c_percent"] is not None:
        out["hba1c_percent"] = {
            "value": float(row["hba1c_percent"]),
            "evidence": f"HbA1c {row['hba1c_percent']}% submitted on the request, drawn {row['hba1c_date']}"}
    else:
        out["hba1c_percent"] = {"value": None, "evidence": "No HbA1c submitted on the request"}

    if row["prior_therapy_fills"]:
        evidence = (f"{row['prior_therapy_fills']} paid {drug} fill(s) since {row['first_fill']}, "
                    f"{row['prior_therapy_days']} days supply")
    else:
        evidence = f"No paid {drug} fills before the request"
    out["prior_therapy_days"] = {"value": int(row["prior_therapy_days"]), "evidence": evidence}

    return out


def lookup(request_ids: list) -> dict:
    """request_id -> facts, for every request found in the warehouse."""
    from pbm.db import connect, rows
    params = {"ids": request_ids,
              "diagnosis": SETTINGS["diabetes_diagnosis_code_prefix"] + "%",
              "drug": SETTINGS["prior_therapy_drug"] + "%"}
    with connect() as conn:
        return {row["request_id"]: facts(row) for row in rows(conn, SQL, params)}


if __name__ == "__main__":
    print(json.dumps(lookup(sys.argv[1:]), indent=2))
