#!/usr/bin/env python3
"""
Generate ACA-like synthetic seed data as CSVs using Faker.
Configure counts and output directory via the constants below, then run without CLI args.
Outputs (timestamped): plans_YYYYMMDDHHMM.csv, providers_YYYYMMDDHHMM.csv, members_YYYYMMDDHHMM.csv, enrollments_YYYYMMDDHHMM.csv, claims_YYYYMMDDHHMM.csv
"""
import csv
import os
import random
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from faker import Faker

# User-configurable parameters
OUT_DIR = "data/seeds"
YEAR = date.today().year
MEMBERS = 5000
PROVIDERS = 30
PLANS = 20
CLAIMS = 5000

SEED = 42

METAL_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]
PROVIDER_SPECIALTIES = [
    "Family Medicine",
    "Internal Medicine",
    "Pediatrics",
    "Cardiology",
    "Dermatology",
    "Orthopedics",
    "OB/GYN",
    "Psychiatry",
    "Oncology",
    "Endocrinology",
    "Gastroenterology",
    "Urology",
    "Neurology",
]

# Additional categorical/value domains for extended member attributes
NETWORK_ACCESS_TYPES = ["HMO", "EPO", "PPO", "POS"]
CLINICAL_SEGMENTS = ["Healthy", "Chronic", "Behavioral", "Maternity", "Complex"]
BROKER_NAMES = ["Acme Brokerage", "HealthLink Brokers", "Prime Advisors", "Value Health Brokers"]
GENERAL_AGENCIES = ["Wellness Group", "Care Partners", "Health Advantage", "Premier Agency"]
SA_CONTRACT_ENTITIES = ["Strategic Alliance A", "Strategic Alliance B", "Strategic Alliance C"]
MUTUALLY_EXCL_HCC = ["Diabetes", "CHF", "COPD", "Asthma", "CKD", None]
CENSUS_REGIONS = {
    "Northeast": {"ME","NH","VT","MA","RI","CT","NY","NJ","PA"},
    "Midwest": {"OH","MI","IN","IL","WI","MN","IA","MO","ND","SD","NE","KS"},
    "South": {"DE","MD","DC","VA","WV","KY","NC","SC","TN","GA","FL","AL","MS","AR","LA","OK","TX"},
    "West": {"MT","ID","WY","CO","NM","AZ","UT","NV","CA","OR","WA","AK","HI"},
}
STATE_TO_REGION = {st: region for region, states in CENSUS_REGIONS.items() for st in states}

CLAIM_STATUS = ["approved", "denied", "pending"]
# Replaced ICD-10 with ICD-11 sample codes
ICD11_SAMPLE = [
    "1A00",  # Cholera due to Vibrio cholerae 01
    "1A01",  # Cholera due to Vibrio cholerae 0139
    "1A02",  # Cholera unspecified
    "1B11",  # Influenza due to identified seasonal influenza virus
    "2A00",  # Acute HIV infection
    "2B20",  # Pulmonary tuberculosis
    "4A00",  # Type 1 diabetes mellitus
    "5A10",  # Major depressive disorder, single episode
    "6A40",  # Epilepsy
    "8A20",  # Malignant neoplasm of breast
    "CA40",  # Osteoarthritis of knee
    "DA0Z",  # Hypertension unspecified
]
CPT_SAMPLE = ["99213", "99214", "80050", "93000", "71046", "36415", "12001"]

# Additional vocabularies to support descriptor fields in objective.md
CLAIM_TYPES = ["Facility", "Professional", "RX"]
MAJOR_SERVICE_CATEGORIES = [
    "Evaluation & Management",
    "Surgery",
    "Radiology",
    "Pathology & Lab",
    "Anesthesia",
    "Medicine",
    "Inpatient",
    "Outpatient",
    "Emergency",
    "Pharmacy",
]
DETAILED_SERVICE_CATEGORIES = [
    "Office Visit Established",
    "Office Visit New",
    "Cardiac Imaging",
    "Basic Metabolic Panel",
    "MRI",
    "CT Scan",
    "Physical Therapy",
    "Infusion Therapy",
    "Generic Medication",
    "Brand Medication",
]
MS_DRG_CODES: List[Tuple[str, str]] = [
    ("291", "Heart failure & shock w MCC"),
    ("292", "Heart failure & shock w CC"),
    ("293", "Heart failure & shock w/o CC/MCC"),
    ("470", "Major joint replacement or reattachment of lower extremity w/o MCC"),
    ("194", "Simple pneumonia & pleurisy w MCC"),
]
MS_DRG_MDC: List[Tuple[str, str]] = [
    ("05", "Diseases & disorders of the circulatory system"),
    ("04", "Diseases & disorders of the respiratory system"),
    ("08", "Diseases & disorders of the musculoskeletal system & connective tissue"),
]
CHANNELS = ["IP", "OP", "SNF", "URG", "OBS", "PRO"]
DRUG_CLASSES = [
    ("Antihypertensives", "ACE Inhibitors", "Lisinopril"),
    ("Antihyperlipidemics", "Statins", "Atorvastatin"),
    ("Antidiabetics", "Biguanides", "Metformin"),
    ("Analgesics", "NSAIDs", "Ibuprofen"),
]
CCSR_SYSTEM = [
    "Circulatory system - Hypertensive disease",
    "Respiratory system - Pneumonia",
    "Musculoskeletal system - Osteoarthritis",
]
CCSR_DESC = [
    "CIR007 - Essential hypertension",
    "RSP002 - Pneumonia (excluding tuberculosis)",
    "MUS004 - Osteoarthritis",
]
PROVIDER_GROUPS = [
    "Downtown Medical Group",
    "Northside Physicians",
    "CareOne Partners",
    "Regional Health Network",
]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def gen_plans(fake: Faker, n: int, year: int) -> List[Dict[str, object]]:
    plans: List[Dict[str, object]] = []
    for i in range(1, n + 1):
        tier = random.choices(METAL_TIERS, weights=[40, 35, 20, 5])[0]
        if tier == "Bronze":
            premium = round(random.uniform(300, 450), 2)
            deductible = random.randrange(6000, 8001, 50)
            oop_max = random.randrange(8000, 9501, 50)
            coins = 0.4
            pcp_copay = 45
        elif tier == "Silver":
            premium = round(random.uniform(400, 650), 2)
            deductible = random.randrange(3000, 5001, 50)
            oop_max = random.randrange(6000, 8001, 50)
            coins = 0.3
            pcp_copay = 35
        elif tier == "Gold":
            premium = round(random.uniform(600, 900), 2)
            deductible = random.randrange(1000, 2501, 50)
            oop_max = random.randrange(3000, 6000, 50)
            coins = 0.2
            pcp_copay = 25
        else:  # Platinum
            premium = round(random.uniform(850, 1200), 2)
            deductible = random.randrange(0, 1001, 50)
            oop_max = random.randrange(1500, 3500, 50)
            coins = 0.1
            pcp_copay = 15

        plans.append(
            {
                "plan_id": f"PLN{i:04d}",
                "name": f"{fake.color_name()} {tier} {year}",
                "metal_tier": tier,
                "monthly_premium": premium,
                "deductible": deductible,
                "oop_max": oop_max,
                "coinsurance_rate": coins,
                "pcp_copay": pcp_copay,
                "effective_year": year,
            }
        )
    return plans


def gen_providers(fake: Faker, n: int) -> List[Dict[str, object]]:
    providers: List[Dict[str, object]] = []
    for i in range(1, n + 1):
        spec = random.choice(PROVIDER_SPECIALTIES)
        street = fake.street_address()
        city = fake.city()
        state = fake.state_abbr()
        zipcode = fake.postcode()
        providers.append(
            {
                "provider_id": f"PRV{i:05d}",
                "npi": f"{random.randrange(10**9, 10**10)}",
                "name": fake.name(),
                "specialty": spec,
                "street": street,
                "city": city,
                "state": state,
                "zip": zipcode,
                "phone": fake.phone_number(),
            }
        )
    return providers


def gen_members(fake: Faker, n: int) -> List[Dict[str, object]]:
    members: List[Dict[str, object]] = []
    for i in range(1, n + 1):
        dob = fake.date_of_birth(minimum_age=0, maximum_age=90)
        street = fake.street_address()
        city = fake.city()
        state = fake.state_abbr()
        zipcode = fake.postcode()
        fpl_ratio = round(random.uniform(0.5, 4.0), 2)
        age = YEAR - dob.year
        if age < 18:
            age_group = "<18"
        elif age < 26:
            age_group = "18-25"
        elif age < 35:
            age_group = "26-34"
        elif age < 45:
            age_group = "35-44"
        elif age < 55:
            age_group = "45-54"
        elif age < 65:
            age_group = "55-64"
        else:
            age_group = "65+"
        plan_network_access_type = random.choice(NETWORK_ACCESS_TYPES)
        plan_metal = random.choice(METAL_TIERS)
        hios_id = f"{random.randint(10000,99999)}{random.randint(100,999)}{random.randint(10,99)}"
        region = STATE_TO_REGION.get(state, random.choice(list(CENSUS_REGIONS.keys())))
        enrollment_length_continuous = random.randint(1, 12)  # months
        clinical_segment = random.choice(CLINICAL_SEGMENTS)
        general_agency_name = random.choice(GENERAL_AGENCIES + [None, None])
        broker_name = random.choice(BROKER_NAMES + [None, None])
        sa_contracting_entity_name = random.choice(SA_CONTRACT_ENTITIES + [None])
        # Engagement/activity counts
        call_count = random.choices([0, 1, 2, 3, 4, 5], weights=[60, 15, 10, 8, 5, 2])[0]
        app_login_count = random.choices([0, 1, 2, 3, 4, 5, 10], weights=[50, 15, 10, 8, 7, 6, 4])[0]
        web_login_count = random.choices([0, 1, 2, 3, 4, 5, 10], weights=[60, 12, 9, 7, 6, 4, 2])[0]
        new_member_in_period = random.choice([0, 1])
        member_used_app = 1 if app_login_count > 0 else 0
        member_had_web_login = 1 if web_login_count > 0 else 0
        member_visited_new_provider_ind = random.choice([0,1])
        high_cost_member = 1 if random.random() < 0.05 else 0
        mutually_exclusive_hcc_condition = random.choice(MUTUALLY_EXCL_HCC)
        geographic_reporting = region
        wisconsin_adi = random.randint(1, 10)
        members.append(
            {
                "member_id": f"MBR{i:06d}",
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "dob": dob.isoformat(),
                "gender": random.choice(["F", "M", "O"]),
                "email": fake.unique.email(),
                "phone": fake.phone_number(),
                "street": street,
                "city": city,
                "state": state,
                "zip": zipcode,
                "fpl_ratio": fpl_ratio,
                # Extended attributes
                "hios_id": hios_id,
                "plan_network_access_type": plan_network_access_type,
                "plan_metal": plan_metal,
                "age_group": age_group,
                "region": region,
                "enrollment_length_continuous": enrollment_length_continuous,
                "clinical_segment": clinical_segment,
                "general_agency_name": general_agency_name,
                "broker_name": broker_name,
                "sa_contracting_entity_name": sa_contracting_entity_name,
                "call_count": call_count,
                "app_login_count": app_login_count,
                "web_login_count": web_login_count,
                "new_member_in_period": new_member_in_period,
                "member_used_app": member_used_app,
                "member_had_web_login": member_had_web_login,
                "member_visited_new_provider_ind": member_visited_new_provider_ind,
                "high_cost_member": high_cost_member,
                "mutually_exclusive_hcc_condition": mutually_exclusive_hcc_condition,
                "geographic_reporting": geographic_reporting,
                "wisconsin_area_deprivation_index": wisconsin_adi,
                "year": YEAR,
            }
        )
    return members


def gen_enrollments(
    members: List[Dict[str, object]],
    plans: List[Dict[str, object]],
    year: int,
    min_days: int = 90,
    max_days: int = 365,
) -> List[Dict[str, object]]:
    # Gracefully handle zero members or zero plans
    if not members or not plans:
        return []
    enrollments: List[Dict[str, object]] = []
    for i, m in enumerate(members, start=1):
        # 85% enrolled; others uninsured
        if random.random() > 0.85:
            continue
        plan = random.choice(plans)
        start = date(year, 1, 1) + timedelta(days=random.randint(0, 120))
        duration = random.randint(min_days, max_days)
        end = start + timedelta(days=duration)
        if end.year > year:
            end = date(year, 12, 31)
        csr_variant = random.choice(["none", "73", "87", "94"])  # cost-sharing reduction variants
        premium_paid = round(plan["monthly_premium"] * random.uniform(0.8, 1.0), 2)
        enrollments.append(
            {
                "enrollment_id": f"ENR{i:06d}",
                "member_id": m["member_id"],
                "plan_id": plan["plan_id"],
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "premium_paid": premium_paid,
                "csr_variant": csr_variant,
            }
        )
    return enrollments


def index_enrollments_by_member(
    enrollments: List[Dict[str, object]]
) -> Dict[str, List[Dict[str, object]]]:
    idx: Dict[str, List[Dict[str, object]]] = {}
    for enr in enrollments:
        idx.setdefault(enr["member_id"], []).append(enr)
    return idx


def pick_active_enrollment(
    enrollments: List[Dict[str, object]],
    on_date: date,
) -> Optional[Dict[str, object]]:
    for enr in enrollments:
        s = datetime.fromisoformat(enr["start_date"]).date()
        e = datetime.fromisoformat(enr["end_date"]).date()
        if s <= on_date <= e:
            return enr
    return None


def gen_claims(
    fake: Faker,
    members: List[Dict[str, object]],
    providers: List[Dict[str, object]],
    plans_by_id: Dict[str, Dict[str, object]],
    enrollments_by_member: Dict[str, List[Dict[str, object]]],
    year: int,
    n_claims: int,
) -> List[Dict[str, object]]:
    # Gracefully handle missing prerequisites
    if not members or not providers or not plans_by_id or not enrollments_by_member:
        return []
    claims: List[Dict[str, object]] = []
    for i in range(1, n_claims + 1):
        m = random.choice(members)
        service_dt = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
        enr = pick_active_enrollment(enrollments_by_member.get(m["member_id"], []), service_dt)
        if not enr:
            # skip if not enrolled on service date
            continue
        prov = random.choice(providers)
        plan = plans_by_id[enr["plan_id"]]
        claim_amount = round(random.uniform(50, 5000), 2)
        allowed_amount = round(claim_amount * random.uniform(0.5, 1.0), 2)
        status = random.choices(CLAIM_STATUS, weights=[0.8, 0.1, 0.1])[0]
        if status == "approved":
            paid_amount = round(allowed_amount * random.uniform(0.5, 1.0), 2)
        else:  # pending or denied
            paid_amount = 0.0

        # Map to clean status values and payment date
        clean_claim_status = {
            "approved": "PAID",
            "denied": "DENIED",
            "pending": "PENDING",
        }[status]
        claim_from = service_dt
        clean_claim_out = None
        if clean_claim_status == "PAID":
            clean_claim_out = claim_from + timedelta(days=random.randint(10, 60))

        # Descriptor enrichments
        claim_type = random.choices(CLAIM_TYPES, weights=[0.15, 0.7, 0.15])[0]
        channel = random.choice(CHANNELS)
        is_oon = 1 if random.random() < 0.12 else 0
        # Specialty: Pharmacy for RX
        provider_specialty = "Pharmacy" if claim_type == "RX" else prov["specialty"]
        major_service_category = (
            "Pharmacy" if claim_type == "RX" else random.choice(MAJOR_SERVICE_CATEGORIES)
        )
        detailed_service_category = random.choice(DETAILED_SERVICE_CATEGORIES)
        ms_drg_code, ms_drg_desc = random.choice(MS_DRG_CODES)
        mdc_code, mdc_desc = random.choice(MS_DRG_MDC)
        # CPT mapping
        cpt = random.choice(CPT_SAMPLE)
        cpt_consumer_description = {
            "99213": "Established patient office visit, low complexity",
            "99214": "Established patient office visit, moderate complexity",
            "80050": "General health panel",
            "93000": "Electrocardiogram, complete",
            "71046": "Chest X-ray",
            "36415": "Collection of venous blood",
            "12001": "Simple repair of superficial wounds",
        }.get(cpt, "Procedure")
        # Procedure hierarchy (toy)
        procedure_level_1 = "Surgery" if cpt in {"12001"} else "Medicine"
        procedure_level_2 = "Office Services" if cpt in {"99213", "99214"} else "Diagnostic"
        procedure_level_3 = "Imaging" if cpt in {"71046", "93000"} else "Other"
        procedure_level_4 = "N/A" if procedure_level_1 != "Surgery" else "Surgical Procedure"
        procedure_level_5 = "N/A" if procedure_level_1 != "Surgery" else "Simple Repair"
        # RX only drug info
        drug_name = drug_class = drug_subclass = drug = None
        if claim_type == "RX":
            dclass, dsub, dname = random.choice(DRUG_CLASSES)
            drug_class = dclass
            drug_subclass = dsub
            drug_name = dname
            drug = dname
        # Contracting entity / provider group
        best_contracting_entity_name = random.choice(SA_CONTRACT_ENTITIES)
        provider_group_name = random.choice(PROVIDER_GROUPS)
        # CCSR
        ccsr_system_description = random.choice(CCSR_SYSTEM)
        ccsr_description = random.choice(CCSR_DESC)
        # Utilization/units
        utilization = 1.0
        hcg_units_days = random.randint(1, 5)
        claims.append(
            {
                "claim_id": f"CLM{i:07d}",
                "member_id": m["member_id"],
                "provider_id": prov["provider_id"],
                "plan_id": plan["plan_id"],
                "service_date": service_dt.isoformat(),
                "claim_amount": claim_amount,
                "allowed_amount": allowed_amount,
                "paid_amount": paid_amount,
                "status": status,
                "diagnosis_code": random.choice(ICD11_SAMPLE),
                "procedure_code": cpt,
                # Descriptor fields and metric primitives
                "charges": claim_amount,
                "allowed": allowed_amount,
                "clean_claim_status": clean_claim_status,
                "claim_from": claim_from.isoformat(),
                "clean_claim_out": clean_claim_out.isoformat() if clean_claim_out else None,
                "utilization": utilization,
                "hcg_units_days": hcg_units_days,
                "claim_type": claim_type,
                "major_service_category": major_service_category,
                "provider_specialty": provider_specialty,
                "detailed_service_category": detailed_service_category,
                "ms_drg": ms_drg_code,
                "ms_drg_description": ms_drg_desc,
                "ms_drg_mdc": mdc_code,
                "ms_drg_mdc_desc": mdc_desc,
                "cpt": cpt,
                "cpt_consumer_description": cpt_consumer_description,
                "procedure_level_1": procedure_level_1,
                "procedure_level_2": procedure_level_2,
                "procedure_level_3": procedure_level_3,
                "procedure_level_4": procedure_level_4,
                "procedure_level_5": procedure_level_5,
                "channel": channel,
                "drug_name": drug_name,
                "drug_class": drug_class,
                "drug_subclass": drug_subclass,
                "drug": drug,
                "is_oon": is_oon,
                "best_contracting_entity_name": best_contracting_entity_name,
                "provider_group_name": provider_group_name,
                "ccsr_system_description": ccsr_system_description,
                "ccsr_description": ccsr_description,
            }
        )
    return claims


def main() -> None:
    # Use config variables instead of CLI args
    out = OUT_DIR
    year = YEAR
    members_n = MEMBERS
    providers_n = PROVIDERS
    plans_n = PLANS
    claims_n = CLAIMS
    seed = SEED

    random.seed(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)

    ensure_dir(out)

    # Append timestamp suffix to output filenames
    ts = datetime.now().strftime("%Y%m%d%H%M")

    plans = gen_plans(fake, plans_n, year)
    providers = gen_providers(fake, providers_n)
    members = gen_members(fake, members_n)
    enrollments = gen_enrollments(members, plans, year)

    enroll_idx = index_enrollments_by_member(enrollments)
    plans_by_id = {p["plan_id"]: p for p in plans}
    claims = gen_claims(fake, members, providers, plans_by_id, enroll_idx, year, claims_n)

    write_csv(
        os.path.join(out, f"plans_{ts}.csv"),
        plans,
        [
            "plan_id",
            "name",
            "metal_tier",
            "monthly_premium",
            "deductible",
            "oop_max",
            "coinsurance_rate",
            "pcp_copay",
            "effective_year",
        ],
    )
    write_csv(
        os.path.join(out, f"providers_{ts}.csv"),
        providers,
        ["provider_id", "npi", "name", "specialty", "street", "city", "state", "zip", "phone"],
    )
    write_csv(
        os.path.join(out, f"members_{ts}.csv"),
        members,
        [
            "member_id",
            "first_name",
            "last_name",
            "dob",
            "gender",
            "email",
            "phone",
            "street",
            "city",
            "state",
            "zip",
            "fpl_ratio",
            "hios_id",
            "plan_network_access_type",
            "plan_metal",
            "age_group",
            "region",
            "enrollment_length_continuous",
            "clinical_segment",
            "general_agency_name",
            "broker_name",
            "sa_contracting_entity_name",
            "call_count",
            "app_login_count",
            "web_login_count",
            "new_member_in_period",
            "member_used_app",
            "member_had_web_login",
            "member_visited_new_provider_ind",
            "high_cost_member",
            "mutually_exclusive_hcc_condition",
            "geographic_reporting",
            "wisconsin_area_deprivation_index",
            "year",
        ],
    )
    write_csv(
        os.path.join(out, f"enrollments_{ts}.csv"),
        enrollments,
        ["enrollment_id", "member_id", "plan_id", "start_date", "end_date", "premium_paid", "csr_variant"],
    )
    write_csv(
        os.path.join(out, f"claims_{ts}.csv"),
        claims,
        [
            "claim_id",
            "member_id",
            "provider_id",
            "plan_id",
            "service_date",
            "claim_amount",
            "allowed_amount",
            "paid_amount",
            "status",
            "diagnosis_code",
            "procedure_code",
            # Added descriptor + metric base fields
            "charges",
            "allowed",
            "clean_claim_status",
            "claim_from",
            "clean_claim_out",
            "utilization",
            "hcg_units_days",
            "claim_type",
            "major_service_category",
            "provider_specialty",
            "detailed_service_category",
            "ms_drg",
            "ms_drg_description",
            "ms_drg_mdc",
            "ms_drg_mdc_desc",
            "cpt",
            "cpt_consumer_description",
            "procedure_level_1",
            "procedure_level_2",
            "procedure_level_3",
            "procedure_level_4",
            "procedure_level_5",
            "channel",
            "drug_name",
            "drug_class",
            "drug_subclass",
            "drug",
            "is_oon",
            "best_contracting_entity_name",
            "provider_group_name",
            "ccsr_system_description",
            "ccsr_description",
        ],
    )

    print(f"Wrote CSVs to: {out} (suffix: _{ts})")


if __name__ == "__main__":
    main()
