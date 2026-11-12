"""Pharmacy claims, formulary, and prior authorization request generation.

Driven by the "pharmacy" block of scripts/scenarios.json and called once per
year from generate_seed_data.py.

Design:
  * Journeys are member-level and keyed off attributes that already exist on the
    member record (mutually_exclusive_hcc_condition, clinical_segment), so the
    pharmacy history agrees with the medical side. Each participating member also
    gets an "anchor" medical office visit carrying the journey diagnosis, which
    the caller turns into a row in claims.csv.
  * Maintenance drugs are filled on a monthly cadence (or 90-day for some
    generics) with realistic refill gaps across the member's enrollment window.
  * Prior authorization journeys produce: the step-therapy fills, a rejected pharmacy claim
    (NCPDP reject 75 = prior authorization required), a prior authorization request with the
    clinical facts that decide it, and, when approved, the subsequent fills.
    The decision is computed by unmet_criteria() below from those facts, so the
    facts are an answer key for anything that later reads a clinical note.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple


def _criterion_met(criterion: dict, facts: dict) -> bool:
    """One policy criterion from scenarios.json against a dict of facts.
    Criteria are either a leaf {field, op, value} or a group {any: [...]} / {all: [...]}."""
    if "any" in criterion:
        return any(_criterion_met(c, facts) for c in criterion["any"])
    if "all" in criterion:
        return all(_criterion_met(c, facts) for c in criterion["all"])
    actual = facts.get(criterion["field"])
    if actual is None:
        return False
    op, value = criterion["op"], criterion["value"]
    return {"eq": actual == value, ">=": actual >= value, "<=": actual <= value, ">": actual > value, "<": actual < value}[op]


def unmet_criteria(policy: dict, facts: dict) -> List[str]:
    """Ids of the criteria the facts fail. An empty list means the request is approved."""
    return [c["id"] for c in policy["criteria"] if not _criterion_met(c, facts)]


REJECT_CODES = {
    "75": "Prior authorization required",
}

PHARMACY_CHAINS = ["CVS Pharmacy", "Walgreens", "Kroger Pharmacy", "Rite Aid", "Costco Pharmacy", "Main Street Drug"]

# Member cost sharing by formulary tier and metal level. Tiers 1-3 are flat
# copays per 30-day fill; tier 4 is coinsurance with a per-fill cap.
COPAY = {
    1: {"Bronze": 15, "Silver": 10, "Gold": 10, "Platinum": 5},
    2: {"Bronze": 60, "Silver": 45, "Gold": 35, "Platinum": 25},
    3: {"Bronze": 110, "Silver": 90, "Gold": 70, "Platinum": 50},
}
COINSURANCE_T4 = {"Bronze": 0.40, "Silver": 0.30, "Gold": 0.25, "Platinum": 0.20}
T4_CAP_PER_FILL = 250.0


def _d(s: str) -> date:
    return datetime.fromisoformat(s).date()


def member_age(member: dict, on: date) -> int:
    dob = _d(member["dob"])
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def gen_pharmacies(n_retail: int = 30) -> List[dict]:
    out = []
    for i in range(n_retail):
        out.append({"npi": f"{random.randrange(10**9, 10**10)}", "name": f"{random.choice(PHARMACY_CHAINS)} #{random.randint(100, 9999)}", "channel": "retail"})
    for name in ["Express Scripts Home Delivery", "CVS Caremark Mail Service"]:
        out.append({"npi": f"{random.randrange(10**9, 10**10)}", "name": name, "channel": "mail"})
    for name in ["Accredo Specialty", "Optum Specialty Pharmacy"]:
        out.append({"npi": f"{random.randrange(10**9, 10**10)}", "name": name, "channel": "specialty"})
    return out


def _pick_pharmacy(pharmacies: List[dict], channel: str) -> dict:
    return random.choice([p for p in pharmacies if p["channel"] == channel])


def _cost_share(tier: int, metal: str, total: float, multiplier: float) -> float:
    if tier >= 4:
        return round(min(total * COINSURANCE_T4[metal], T4_CAP_PER_FILL * multiplier), 2)
    return round(min(COPAY[tier][metal] * multiplier, total), 2)


class PharmacyGenerator:
    def __init__(self, cfg: dict, providers_by_specialty: Dict[str, List[dict]], all_providers: List[dict]):
        self.cfg = cfg
        self.formulary: Dict[str, dict] = {f["ndc"]: f for f in cfg["formulary"]}
        self.journeys = cfg["journeys"]
        self.policies = cfg["prior_authorization_policies"]
        self.providers_by_specialty = providers_by_specialty
        self.all_providers = all_providers
        self.pharmacies = gen_pharmacies()
        self.claim_seq = 0
        self.prior_authorization_seq = 0

    # ----------------------------------------------------------------- helpers
    def _provider(self, specialty: str) -> dict:
        return random.choice(self.providers_by_specialty.get(specialty) or self.all_providers)

    def _fill_row(self, year: int, member: dict, plan: dict, prescriber: dict, drug: dict, fill_date: date,
                  refill_number: int, ninety_day: bool, status: str = "paid", reject_code: Optional[str] = None,
                  prior_authorization_request_id: Optional[str] = None) -> dict:
        self.claim_seq += 1
        mult = 3 if ninety_day else 1
        if drug["is_specialty"]:
            pharmacy = _pick_pharmacy(self.pharmacies, "specialty")
        elif ninety_day:
            pharmacy = _pick_pharmacy(self.pharmacies, "mail")
        else:
            pharmacy = _pick_pharmacy(self.pharmacies, "retail")
        lo, hi = drug["cost_per_fill"]
        ingredient = round(random.uniform(lo, hi) * mult * (0.95 if ninety_day else 1.0), 2)
        fee = 0.0 if pharmacy["channel"] == "mail" else round(random.uniform(1.0, 2.5), 2)
        total = round(ingredient + fee, 2)
        copay = _cost_share(drug["tier"], plan["metal_tier"], total, mult)
        plan_paid = round(total - copay, 2)
        if status != "paid":
            ingredient = fee = copay = plan_paid = 0.0
        return {
            "pharmacy_claim_id": f"RXC{year}{self.claim_seq:07d}",
            "member_id": member["member_id"],
            "plan_id": plan["plan_id"],
            "prescriber_id": prescriber["provider_id"],
            "pharmacy_npi": pharmacy["npi"],
            "pharmacy_name": pharmacy["name"],
            "channel": pharmacy["channel"],
            "fill_date": fill_date.isoformat(),
            "ndc": drug["ndc"],
            "drug_name": drug["drug_name"],
            "generic_name": drug["generic_name"],
            "brand_name": drug["brand_name"],
            "drug_class": drug["drug_class"],
            "drug_subclass": drug["drug_subclass"],
            "is_generic": drug["is_generic"],
            "is_specialty": drug["is_specialty"],
            "formulary_tier": drug["tier"],
            "days_supply": drug["days_supply"] * mult,
            "quantity": drug["quantity_per_fill"] * mult,
            "refill_number": refill_number,
            "ingredient_cost": ingredient,
            "dispensing_fee": fee,
            "member_copay": copay,
            "plan_paid": plan_paid,
            "claim_status": status,
            "reject_code": reject_code,
            "reject_description": REJECT_CODES.get(reject_code) if reject_code else None,
            "prior_authorization_request_id": prior_authorization_request_id,
        }

    def _fill_series(self, year: int, member: dict, plan: dict, prescriber: dict, drug: dict, start: date, end: date,
                     max_fills: Optional[int] = None, prior_authorization_request_id: Optional[str] = None) -> List[dict]:
        """Fills from start through end on a refill cadence with realistic gaps."""
        ninety_day = bool(drug["is_generic"]) and drug["days_supply"] >= 30 and random.random() < 0.6
        fills: List[dict] = []
        d = start
        n = 0
        while d <= end and (max_fills is None or n < max_fills):
            status = "reversed" if random.random() < 0.01 else "paid"
            fills.append(self._fill_row(year, member, plan, prescriber, drug, d, n, ninety_day, status=status, prior_authorization_request_id=prior_authorization_request_id))
            n += 1
            gap = drug["days_supply"] * (3 if ninety_day else 1) + random.randint(-3, 10)
            if random.random() < 0.08:
                gap += random.randint(15, 40)  # missed refill
            d = d + timedelta(days=gap)
        return fills

    # ------------------------------------------------------------ truth facts
    def _draw_truth(self, policy_id: str, age: int, prescriber: dict) -> dict:
        """Draw the clinical facts that decide a prior authorization, with deliberate mass near
        each threshold so the reviewer's "route to human" behaviour is tested."""
        f: dict = {"age": age}
        if policy_id == "glp1_type2_diabetes":
            f["step_category"] = random.choices(["adequate", "short", "none", "intolerance"], [0.81, 0.08, 0.05, 0.06])[0]
            f["has_type2_diabetes_diagnosis"] = random.random() < 0.96
            if random.random() < 0.15:
                f["hba1c_percent"] = round(random.uniform(6.6, 7.4), 1)   # near the 7.0 threshold
            else:
                f["hba1c_percent"] = round(min(12.5, max(6.0, random.gauss(8.6, 0.9))), 1)
            f["bmi"] = round(min(55, max(22, random.gauss(33, 5))), 1)
            f["prior_therapy_drug"] = "metformin"
            f["prior_therapy_intolerance"] = f["step_category"] == "intolerance"
            f["medullary_thyroid_cancer_history"] = random.random() < 0.025
            f["taking_another_glp1"] = random.random() < 0.015
        elif policy_id == "glp1_weight_management":
            f["step_category"] = "n/a"
            f["has_type2_diabetes_diagnosis"] = False
            f["bmi"] = round(random.uniform(26.0, 31.0), 1) if random.random() < 0.2 else round(min(55, max(25, random.gauss(35, 4.5))), 1)
            comorbidities = [c for c in ["hypertension", "dyslipidemia", "obstructive sleep apnea", "prediabetes"] if random.random() < 0.4]
            f["weight_comorbidities"] = ";".join(comorbidities)
            f["weight_comorbidity_count"] = len(comorbidities)
            f["lifestyle_program_months"] = random.choices([0, 1, 2, 3, 4, 6, 9, 12], [0.08, 0.08, 0.10, 0.20, 0.18, 0.16, 0.10, 0.10])[0]
            f["medullary_thyroid_cancer_history"] = random.random() < 0.03
            f["taking_another_glp1"] = random.random() < 0.02
        elif policy_id == "adalimumab_rheumatoid_arthritis":
            f["step_category"] = random.choices(["adequate", "short", "none", "intolerance"], [0.70, 0.12, 0.08, 0.10])[0]
            f["has_rheumatoid_arthritis_diagnosis"] = random.random() < 0.95
            f["prior_therapy_drug"] = "methotrexate"
            f["prior_therapy_intolerance"] = f["step_category"] == "intolerance"
            f["tuberculosis_screen_negative"] = random.random() < 0.90
            f["rheumatology_consult"] = True if prescriber["specialty"] == "Rheumatology" else random.random() < 0.3
        else:
            raise ValueError(policy_id)
        return f

    # ------------------------------------------------------------- prior authorization journey
    def _run_prior_authorization(self, year: int, journey: dict, member: dict, plan: dict, enr_start: date, enr_end: date,
                claims: List[dict], prior_authorization_requests: List[dict], anchors: List[dict]) -> None:
        prior_authorization_cfg = journey["prior_authorization_attempt"]
        policy_id = prior_authorization_cfg["policy"]
        # 15% of prior authorization requests come from primary care rather than the specialist
        prescriber = self._provider("Family Medicine" if random.random() < 0.15 else journey["anchor_specialty"])
        window = (enr_end - enr_start).days
        truth = self._draw_truth(policy_id, member_age(member, enr_start), prescriber)
        step_ndc = prior_authorization_cfg.get("step_ndc")
        step_drug = self.formulary[step_ndc] if step_ndc else None

        # Step-therapy fills, then the attempt date that follows them
        step_fills: List[dict] = []
        cat = truth["step_category"]
        if step_drug and cat in ("adequate", "short", "intolerance"):
            k = {"adequate": random.randint(3, 8), "short": random.randint(1, 2), "intolerance": random.randint(0, 1)}[cat]
            k = max(0, min(k, (window - 40) // 30))
            start = enr_start + timedelta(days=random.randint(0, 20))
            if k > 0:
                series = self._fill_series(year, member, plan, prescriber, step_drug, start, enr_end, max_fills=None if cat == "adequate" else k)
                # For "adequate" the member stays on metformin, so the attempt lands after k fills
                step_fills = series
                anchor_fill = series[min(k, len(series)) - 1]
                attempt = _d(anchor_fill["fill_date"]) + timedelta(days=random.randint(10, 25))
            else:
                attempt = start + timedelta(days=random.randint(10, 40))
        else:
            attempt = enr_start + timedelta(days=random.randint(10, min(60, max(11, window - 30))))
        if attempt > enr_end - timedelta(days=14):
            attempt = enr_end - timedelta(days=14)
        claims.extend(step_fills)

        paid_step = [f for f in step_fills if f["claim_status"] == "paid" and _d(f["fill_date"]) < attempt]
        truth["prior_therapy_days"] = sum(f["days_supply"] for f in paid_step) if step_drug else None
        truth["prior_therapy_start_date"] = paid_step[0]["fill_date"] if paid_step else None
        if step_drug and cat == "none":
            truth["prior_therapy_days"] = 0

        # Requested drug, rejected claim, prior authorization request
        ndcs, weights = zip(*prior_authorization_cfg["drug_choices"])
        drug = self.formulary[random.choices(ndcs, weights)[0]]
        self.prior_authorization_seq += 1
        prior_authorization_id = f"PA{year}{self.prior_authorization_seq:06d}"
        claims.append(self._fill_row(year, member, plan, prescriber, drug, attempt, 0, False, status="rejected", reject_code="75", prior_authorization_request_id=prior_authorization_id))

        request_date = attempt + timedelta(days=random.randint(0, 2))
        urgency = "expedited" if random.random() < 0.10 else "standard"
        turnaround = random.randint(0, 2) if urgency == "expedited" else random.randint(1, 7)
        decision_date = request_date + timedelta(days=turnaround)
        unmet = unmet_criteria(self.policies[policy_id], truth)
        decision = "approved" if not unmet else "denied"

        first_fill_date = None
        if decision == "approved":
            ff = decision_date + timedelta(days=random.randint(1, 10))
            if ff <= enr_end:
                first_fill_date = ff
                persist = random.randint(1, 3) if random.random() < 0.15 else None
                claims.extend(self._fill_series(year, member, plan, prescriber, drug, ff, enr_end, max_fills=persist, prior_authorization_request_id=prior_authorization_id))

        # Anchor visit shortly before the request: the one with the labs
        diagnosis = journey["anchor_diagnosis"]
        if policy_id == "glp1_type2_diabetes" and not truth["has_type2_diabetes_diagnosis"]:
            diagnosis = "R7303"  # prediabetes
        if policy_id == "adalimumab_rheumatoid_arthritis" and not truth["has_rheumatoid_arthritis_diagnosis"]:
            diagnosis = "M199"   # unspecified osteoarthritis
        visit = request_date - timedelta(days=random.randint(3, 45))
        if visit < enr_start:
            visit = enr_start
        anchors.append({"member": member, "plan": plan, "provider": prescriber, "date": visit, "diagnosis": diagnosis})
        hba1c_date = visit if policy_id == "glp1_type2_diabetes" else None

        prior_authorization_requests.append({
            "prior_authorization_request_id": prior_authorization_id,
            "member_id": member["member_id"],
            "plan_id": plan["plan_id"],
            "prescriber_id": prescriber["provider_id"],
            "prescriber_specialty": prescriber["specialty"],
            "policy_id": policy_id,
            "ndc": drug["ndc"],
            "drug_name": drug["drug_name"],
            "request_date": request_date.isoformat(),
            "decision_date": decision_date.isoformat(),
            "turnaround_days": turnaround,
            "urgency": urgency,
            "decision": decision,
            "denial_reasons": ";".join(unmet) if unmet else None,
            "first_fill_date": first_fill_date.isoformat() if first_fill_date else None,
            "diagnosis_code": diagnosis,
            "age_at_request": member_age(member, request_date),
            "has_type2_diabetes_diagnosis": truth.get("has_type2_diabetes_diagnosis"),
            "has_rheumatoid_arthritis_diagnosis": truth.get("has_rheumatoid_arthritis_diagnosis"),
            "hba1c_percent": truth.get("hba1c_percent"),
            "hba1c_date": hba1c_date.isoformat() if hba1c_date else None,
            "bmi": truth.get("bmi"),
            "weight_comorbidities": truth.get("weight_comorbidities"),
            "weight_comorbidity_count": truth.get("weight_comorbidity_count"),
            "lifestyle_program_months": truth.get("lifestyle_program_months"),
            "prior_therapy_drug": truth.get("prior_therapy_drug"),
            "prior_therapy_days": truth.get("prior_therapy_days"),
            "prior_therapy_start_date": truth.get("prior_therapy_start_date"),
            "prior_therapy_intolerance": truth.get("prior_therapy_intolerance"),
            "medullary_thyroid_cancer_history": truth.get("medullary_thyroid_cancer_history"),
            "taking_another_glp1": truth.get("taking_another_glp1"),
            "tuberculosis_screen_negative": truth.get("tuberculosis_screen_negative"),
            "rheumatology_consult": truth.get("rheumatology_consult"),
        })

    # ----------------------------------------------------------------- driver
    def gen_year(self, year: int, members: List[dict], plans_by_id: Dict[str, dict],
                 enrollments_by_member: Dict[str, List[dict]]) -> Tuple[List[dict], List[dict], List[dict]]:
        """Return (pharmacy_claims, prior_authorization_requests, anchor_visits) for one year."""
        claims: List[dict] = []
        prior_authorization_requests: List[dict] = []
        anchors: List[dict] = []
        for member in members:
            enrs = enrollments_by_member.get(member["member_id"])
            if not enrs:
                continue
            enr = enrs[0]
            plan = plans_by_id[enr["plan_id"]]
            enr_start, enr_end = _d(enr["start_date"]), _d(enr["end_date"])
            window = (enr_end - enr_start).days
            age = member_age(member, enr_start)

            for journey in self.journeys:
                if any(member.get(k) != v for k, v in journey["anchor"].items()):
                    continue
                if age < journey["min_age"] or random.random() >= journey["participation"]:
                    continue

                prior_authorization_cfg = journey.get("prior_authorization_attempt")
                # Step therapy needs ~90 days of fills before the request, so PA
                # attempts with a step drug need a long enough enrollment window
                min_window = 140 if (prior_authorization_cfg and prior_authorization_cfg.get("step_ndc")) else 75
                do_prior_authorization = bool(prior_authorization_cfg) and window >= min_window and random.random() < prior_authorization_cfg["rate_by_year"].get(str(year), 0)
                maintenance = list(journey.get("maintenance", []))
                if do_prior_authorization:
                    # The prior authorization path owns the step drug, so drop it from plain maintenance
                    maintenance = [m for m in maintenance if m["ndc"] != prior_authorization_cfg.get("step_ndc")]
                    self._run_prior_authorization(year, journey, member, plan, enr_start, enr_end, claims, prior_authorization_requests, anchors)
                elif journey.get("anchor_diagnosis"):
                    prov = self._provider(journey["anchor_specialty"])
                    anchors.append({"member": member, "plan": plan, "provider": prov, "date": enr_start + timedelta(days=random.randint(5, max(6, min(90, window)))), "diagnosis": journey["anchor_diagnosis"]})

                prescriber = self._provider(journey["anchor_specialty"])
                for m in maintenance:
                    if random.random() < m["p"]:
                        start = enr_start + timedelta(days=random.randint(0, max(0, min(45, window // 3))))
                        claims.extend(self._fill_series(year, member, plan, prescriber, self.formulary[m["ndc"]], start, enr_end))
                for a in journey.get("acute", []):
                    if random.random() < a["p"]:
                        d = enr_start + timedelta(days=random.randint(0, max(0, window)))
                        claims.append(self._fill_row(year, member, plan, self._provider("Family Medicine"), self.formulary[a["ndc"]], d, 0, False))
        claims.sort(key=lambda r: (r["fill_date"], r["pharmacy_claim_id"]))
        return claims, prior_authorization_requests, anchors

    def formulary_rows(self) -> List[dict]:
        rows = []
        for f in self.cfg["formulary"]:
            rows.append({
                "ndc": f["ndc"], "drug_name": f["drug_name"], "generic_name": f["generic_name"], "brand_name": f["brand_name"],
                "drug_class": f["drug_class"], "drug_subclass": f["drug_subclass"], "is_generic": f["is_generic"],
                "is_specialty": f["is_specialty"], "formulary_tier": f["tier"], "requires_prior_authorization": f["requires_prior_authorization"],
                "prior_authorization_policy_id": f["prior_authorization_policy"], "quantity_limit_per_fill": f["quantity_per_fill"],
                "standard_days_supply": f["days_supply"], "wac_per_fill_low": f["cost_per_fill"][0], "wac_per_fill_high": f["cost_per_fill"][1],
            })
        return rows


PHARMACY_CLAIM_FIELDS = [
    "pharmacy_claim_id", "member_id", "plan_id", "prescriber_id", "pharmacy_npi", "pharmacy_name", "channel", "fill_date",
    "ndc", "drug_name", "generic_name", "brand_name", "drug_class", "drug_subclass", "is_generic", "is_specialty", "formulary_tier",
    "days_supply", "quantity", "refill_number", "ingredient_cost", "dispensing_fee", "member_copay", "plan_paid",
    "claim_status", "reject_code", "reject_description", "prior_authorization_request_id",
]

PRIOR_AUTHORIZATION_REQUEST_FIELDS = [
    "prior_authorization_request_id", "member_id", "plan_id", "prescriber_id", "prescriber_specialty", "policy_id", "ndc", "drug_name",
    "request_date", "decision_date", "turnaround_days", "urgency", "decision", "denial_reasons", "first_fill_date",
    "diagnosis_code", "age_at_request", "has_type2_diabetes_diagnosis", "has_rheumatoid_arthritis_diagnosis", "hba1c_percent", "hba1c_date", "bmi", "weight_comorbidities",
    "weight_comorbidity_count", "lifestyle_program_months", "prior_therapy_drug", "prior_therapy_days",
    "prior_therapy_start_date", "prior_therapy_intolerance", "medullary_thyroid_cancer_history", "taking_another_glp1",
    "tuberculosis_screen_negative", "rheumatology_consult",
]

FORMULARY_FIELDS = [
    "ndc", "drug_name", "generic_name", "brand_name", "drug_class", "drug_subclass", "is_generic", "is_specialty",
    "formulary_tier", "requires_prior_authorization", "prior_authorization_policy_id", "quantity_limit_per_fill", "standard_days_supply",
    "wac_per_fill_low", "wac_per_fill_high",
]
