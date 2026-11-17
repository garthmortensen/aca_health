"""Add synthetic clinical notes for GLP-1 (type 2 diabetes) prior authorization requests that need review.

The facts on each request in the warehouse were generated first (scripts/gen_pharmacy.py) and
decided the outcome. Claude turns those facts into a progress note, so every note comes with an
answer key (`truth`, `truth_evaluation`, `expected_action`) in the same shape as the existing
pbm/data/notes.jsonl. New notes are appended; requests that already have a note are skipped.

Every note produced here is meant to land with a nurse practitioner, for one of two reasons:
  policy   the facts miss or nearly miss a criterion (denial, or a borderline lab / step therapy)
           so the system cannot approve on its own. Some of these notes are also messy.
  omission an eligible request whose note is messy and leaves out 1-2 policy facts, so the
           system cannot confirm them from the note.

Usage:
  python -m pbm.generate_notes --dry-run          # show the selection, write nothing
  python -m pbm.generate_notes --count 50         # write notes, append to pbm/data/notes.jsonl

Everything produced here is fictional. Never put real patient text in this repo or in API calls.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import anthropic
import duckdb
import pandas as pd

from pbm.db import DB_PATH

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NOTES_PATH = os.path.join(HERE, "data", "notes.jsonl")
SCENARIOS = os.path.join(REPO, "scripts", "scenarios.json")
PROVIDERS = os.path.join(REPO, "transform", "seeds", "providers.csv")
MODEL = "claude-opus-5-5"
POLICY_ID = "glp1_type2_diabetes"

# Facts a note for this policy has to document
FIELDS = ["has_type2_diabetes_diagnosis", "age", "hba1c_percent", "prior_therapy_days",
          "prior_therapy_intolerance", "medullary_thyroid_cancer_history", "taking_another_glp1"]
# Same keys as the existing notes' `truth`
TRUTH_KEYS = ["has_type2_diabetes_diagnosis", "has_rheumatoid_arthritis_diagnosis", "age", "hba1c_percent", "bmi",
              "weight_comorbidity_count", "weight_comorbidities", "lifestyle_program_months", "prior_therapy_drug",
              "prior_therapy_days", "prior_therapy_intolerance", "medullary_thyroid_cancer_history",
              "taking_another_glp1", "tuberculosis_screen_negative", "rheumatology_consult"]

LABELS = {
    "has_type2_diabetes_diagnosis": "type 2 diabetes diagnosis documented",
    "age": "patient age (years)",
    "hba1c_percent": "most recent HbA1c (%)",
    "prior_therapy_days": "metformin duration",
    "prior_therapy_intolerance": "intolerance or contraindication to metformin",
    "medullary_thyroid_cancer_history": "personal or family history of medullary thyroid carcinoma or MEN2",
    "taking_another_glp1": "currently taking another GLP-1 receptor agonist",
}

SYSTEM_PROMPT = """You write synthetic clinical documentation used to test prior-authorization software. Every patient, clinician, and detail is fictional; you are given the facts and must not invent clinical facts that contradict them.

Rules:
1. Every fact in FACTS_TO_DOCUMENT must appear in the note with the same value. Numbers must match exactly (an HbA1c of 7.3 must read 7.3%, not "around 7"). Express therapy duration as a duration (for example "on metformin for about 5 months", or the start month plus "ongoing"), consistent with the months given.
2. When a boolean fact is false, document the negative explicitly the way a clinician would (for example "no personal or family history of medullary thyroid carcinoma or MEN2", "not currently taking any other GLP-1 agent", "tolerating metformin well").
3. Do not mention, hint at, or leave placeholders for anything in OMIT_ENTIRELY. The note should read as if the clinician simply did not record it.
4. You may add realistic filler consistent with the facts: vitals, a medication list, exam findings, a plan. Filler must never contradict a listed fact and must not introduce facts that change coverage eligibility.
5. Do not mention insurance policy criteria, checklists, or this instruction set. The note is written by the clinician for the chart, with a closing line requesting the medication. Where a fact is unfavorable (a low HbA1c, a short metformin trial, a diagnosis of prediabetes), the clinician still writes the request; they do not argue that the criteria are met.
6. Output only the note text.

STYLE guidance:
- clean: a complete progress note with headers (HPI, PMH, Medications, Labs, Assessment, Plan), full sentences, 250-450 words.
- messy: telegraphic clinic shorthand, heavy abbreviations (pt, hx, c/o, DM2, MTX, f/u), inconsistent capitalization and spacing, 2-4 realistic typos, no neat headers, 120-250 words. Facts still present (unless omitted) but you have to look for them."""


# ---- policy evaluation (same semantics as the archived pbm/policy.py) ----
def _eval(c: dict, facts: dict) -> tuple[str, bool]:
    if "any" in c or "all" in c:
        kids = [_eval(k, facts) for k in c.get("any", c.get("all"))]
        statuses = [s for s, _ in kids]
        if "any" in c:
            if "met" in statuses:
                return "met", any(n for s, n in kids if s == "met")
            return ("unknown" if "unknown" in statuses else "unmet"), any(n for _, n in kids)
        if "unmet" in statuses:
            return "unmet", any(n for _, n in kids)
        return ("unknown" if "unknown" in statuses else "met"), any(n for _, n in kids)
    actual = facts.get(c["field"])
    if actual is None:
        return "unknown", False
    ok = {"eq": actual == c["value"], ">=": actual >= c["value"]}[c["op"]]
    near = "near" in c and not isinstance(actual, bool) and round(abs(float(actual) - float(c["value"])), 6) < float(c["near"])
    return ("met" if ok else "unmet"), near


def evaluate(policy: dict, facts: dict) -> dict:
    met, unmet, unknown, near = [], [], [], []
    for c in policy["criteria"]:
        status, is_near = _eval(c, facts)
        {"met": met, "unmet": unmet, "unknown": unknown}[status].append(c["id"])
        if is_near:
            near.append(c["id"])
    outcome = "deny" if unmet else "unknown" if unknown else "approve"
    return {"outcome": outcome, "unmet": unmet, "unknown": unknown, "near_threshold": near}


# ---- selection ----
def py(v):
    if v is None or (isinstance(v, float) and v != v) or v is pd.NA or v is pd.NaT:
        return None
    return v.item() if hasattr(v, "item") else v


def load_candidates(policy: dict) -> pd.DataFrame:
    noted = {json.loads(line)["prior_authorization_request_id"] for line in open(NOTES_PATH)}
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.sql(f"""
        select p.*, m.first_name, m.last_name, m.date_of_birth, m.gender
        from dw.fct_prior_authorization_request p
        join dw.dim_member m on m.member_id = p.member_id and m.is_current
        where p.policy_id = '{POLICY_ID}'""").df()
    con.close()
    df = df[~df.prior_authorization_request_id.isin(noted)].copy()
    prov = pd.read_csv(PROVIDERS, dtype=str).set_index("provider_id")["name"]
    df["prescriber_name"] = df.prescriber_id.map(prov)
    df["truth"] = df.apply(truth_of, axis=1)
    df["evaluation"] = df.truth.map(lambda t: evaluate(policy, t))
    return df


def truth_of(row) -> dict:
    t = {k: py(row.get(k)) for k in TRUTH_KEYS}
    t["age"] = int(row["age_at_request"])
    for k in ("weight_comorbidity_count", "prior_therapy_days"):
        if t[k] is not None:
            t[k] = int(t[k])
    if t["hba1c_percent"] is not None:
        t["hba1c_percent"] = float(t["hba1c_percent"])
    if t["bmi"] is not None:
        t["bmi"] = float(t["bmi"])
    return t


def select(df: pd.DataFrame, policy: dict, count: int, rng: random.Random, messy_share: float) -> list[tuple]:
    """(row, style, omitted, reason) tuples. Roughly half policy-driven, half omission-driven."""
    ev = df.evaluation
    policy_pool = df[ev.map(lambda e: e["outcome"] == "deny" or bool(e["near_threshold"]))]
    clean_pool = df[ev.map(lambda e: e["outcome"] == "approve" and not e["near_threshold"])]
    n_policy = min(len(policy_pool), count // 2)
    n_omit = count - n_policy
    # Put near misses first within the policy pool, then fill with denials, so borderline cases are well represented
    near = policy_pool[policy_pool.evaluation.map(lambda e: bool(e["near_threshold"]))]
    far = policy_pool.drop(near.index)
    picked_policy = pd.concat([near.sample(n=min(len(near), n_policy // 2), random_state=rng.randint(0, 2**31)),
                               far.sample(n=min(len(far), n_policy), random_state=rng.randint(0, 2**31))]).head(n_policy)
    if len(picked_policy) < n_policy:
        rest = policy_pool.drop(picked_policy.index)
        picked_policy = pd.concat([picked_policy, rest.head(n_policy - len(picked_policy))])
    picked_omit = clean_pool.sample(n=n_omit, random_state=rng.randint(0, 2**31))

    out = []
    for _, row in picked_policy.iterrows():
        style = "messy" if rng.random() < messy_share else "clean"
        out.append((row, style, [], "policy"))
    for _, row in picked_omit.iterrows():
        # Only omit facts whose absence leaves a criterion unresolved. Dropping the intolerance
        # fact when the metformin trial already passes would not need review at all.
        candidates = [f for f in FIELDS if f != "age" and row.truth.get(f) is not None
                      and evaluate(policy, {**row.truth, f: None})["outcome"] == "unknown"]
        first = rng.choice(candidates)
        extra = [f for f in FIELDS if f not in ("age", first) and row.truth.get(f) is not None]
        omitted = [first] + (rng.sample(extra, 1) if rng.random() < 0.35 else [])
        out.append((row, "messy", omitted, "omission"))
    rng.shuffle(out)
    return out


# ---- note writing ----
def facts_for_prompt(row, omitted: list[str]) -> dict:
    t = row.truth
    out = {}
    for f in FIELDS:
        if f in omitted or t.get(f) is None:
            continue
        v, label = t[f], LABELS[f]
        if f == "prior_therapy_days":
            v = "never tried" if v == 0 else f"about {round(v / 30.0, 1):g} months"
        elif f == "hba1c_percent":
            v = f"{v} (drawn {row.hba1c_date})" if py(row.hba1c_date) else v
        out[label] = v
    if t.get("has_type2_diabetes_diagnosis") is False and "has_type2_diabetes_diagnosis" not in omitted:
        out[LABELS["has_type2_diabetes_diagnosis"]] = "no - patient has prediabetes, not type 2 diabetes"
    return out


def build_context(row, style: str, omitted: list[str]) -> dict:
    start = py(row.prior_therapy_start_date)
    return {
        "note_date": str(row.request_date)[:10],
        "patient": {"name": f"{row.first_name} {row.last_name}", "sex": {"F": "female", "M": "male"}.get(row.gender, "nonbinary"),
                    "date_of_birth": str(row.date_of_birth)[:10], "age": int(row.age_at_request)},
        "clinician": {"name": row.prescriber_name, "specialty": row.prescriber_specialty},
        "medication_requested": row.drug_name,
        "therapy_start_month": datetime.fromisoformat(str(start)[:10]).strftime("%B %Y") if start else None,
        "FACTS_TO_DOCUMENT": facts_for_prompt(row, omitted),
        "OMIT_ENTIRELY": [LABELS[f] for f in omitted],
        "STYLE": style,
    }


def write_note(client: anthropic.Anthropic, ctx: dict) -> dict:
    resp = client.messages.create(
        model=MODEL, max_tokens=3000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Write the note for this encounter.\n\n" + json.dumps(ctx, indent=2, default=str)}])
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return {"note": text or None, "stop_reason": resp.stop_reason, "usage": usage}


def record(row, style: str, omitted: list[str], res: dict, policy: dict) -> dict:
    truth = row.truth
    documented = {k: (None if k in omitted else v) for k, v in truth.items()}
    ev_doc = evaluate(policy, documented)
    return {
        "prior_authorization_request_id": row.prior_authorization_request_id,
        "member_id": row.member_id,
        "policy_id": POLICY_ID,
        "drug_name": row.drug_name,
        "request_date": str(row.request_date)[:10],
        "prescriber_specialty": row.prescriber_specialty,
        "style": style,
        "omitted_fields": omitted,
        "note": res["note"],
        "stop_reason": res["stop_reason"],
        "truth": truth,
        "truth_decision": row.decision,
        "truth_evaluation": {"outcome": row.evaluation["outcome"], "unmet": row.evaluation["unmet"],
                             "near_threshold": row.evaluation["near_threshold"]},
        "expected_action": "auto_approve" if (ev_doc["outcome"] == "approve" and not omitted and not ev_doc["near_threshold"]) else "route_to_human",
        "expected_recommendation": {"approve": "approve", "deny": "deny", "unknown": "needs_info"}[ev_doc["outcome"]],
        "usage": res["usage"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--count", type=int, default=50)
    p.add_argument("--messy-share", type=float, default=0.4, help="share of policy-driven notes written messy")
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    policy = json.load(open(SCENARIOS))["pharmacy"]["prior_authorization_policies"][POLICY_ID]
    rng = random.Random(args.seed)
    chosen = select(load_candidates(policy), policy, args.count, rng, args.messy_share)
    print(f"Selected {len(chosen)}: " + ", ".join(f"{k}={sum(1 for c in chosen if c[3] == k)}" for k in ("policy", "omission")))
    if args.dry_run:
        for row, style, omitted, reason in chosen:
            print(row.prior_authorization_request_id, reason, style, omitted, row.evaluation["unmet"], row.evaluation["near_threshold"])
        return

    client = anthropic.Anthropic(max_retries=3)
    jobs = [(row, style, omitted, build_context(row, style, omitted)) for row, style, omitted, _ in chosen]
    with ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(lambda j: write_note(client, j[3]), jobs))

    records = [record(r, s, o, res, policy) for (r, s, o, _), res in zip(jobs, results) if res["note"]]
    with open(NOTES_PATH, "a") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    tin = sum(r["usage"]["input_tokens"] for r in records)
    tout = sum(r["usage"]["output_tokens"] for r in records)
    print(f"Appended {len(records)}/{len(jobs)} notes to {NOTES_PATH} ({tin} in / {tout} out tokens)")


if __name__ == "__main__":
    main()
