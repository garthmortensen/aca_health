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
from typing import Dict, List, Optional

from faker import Faker

# User-configurable parameters
OUT_DIR = "data/seeds"
YEAR = date.today().year
MEMBERS = 5000
PROVIDERS = 0
PLANS = 0
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
CLAIM_STATUS = ["approved", "denied", "pending"]
ICD10_SAMPLE = ["E11.9", "I10", "J06.9", "M54.50", "Z00.00", "R51.9", "K21.9"]
CPT_SAMPLE = ["99213", "99214", "80050", "93000", "71046", "36415", "12001"]


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
        fpl_ratio = round(random.uniform(0.5, 4.0), 2)  # ACA subsidy-like context
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
                "diagnosis_code": random.choice(ICD10_SAMPLE),
                "procedure_code": random.choice(CPT_SAMPLE),
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
        ],
    )

    print(f"Wrote CSVs to: {out} (suffix: _{ts})")


if __name__ == "__main__":
    main()
