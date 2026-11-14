"""Build pbm/data/pbm.duckdb from the local Postgres warehouse.

Copies only what the app reads: every prior authorization request, and the
members, medical claims and pharmacy claims of the members who made one. The
existing paper trail (review.prior_authorization_decision) is copied too, so
decisions already recorded carry over.

Runs locally, where Postgres is. The hosted app only reads the file this writes.
Connection settings come from the repo's .env (POSTGRES_USER / POSTGRES_PASSWORD /
POSTGRES_DB) or PG* environment variables.

Usage:
  python -m pbm.build_db                 # rebuild pbm/data/pbm.duckdb
  python -m pbm.build_db --no-review     # warehouse only, empty paper trail
"""
from __future__ import annotations

import argparse
import os

import duckdb

from pbm.db import DB_PATH, REVIEW_DDL

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Members who made a prior authorization request; the rest of the warehouse is not needed
PA_MEMBERS = "member_id in (select member_id from pg.dw.fct_prior_authorization_request)"

TABLES = {
    "fct_prior_authorization_request": "select * from pg.dw.fct_prior_authorization_request",
    "dim_member": f"select member_id, date_of_birth, gender, state, is_current from pg.dw.dim_member where {PA_MEMBERS}",
    "fct_claim": f"select claim_id, member_id, claim_date, diagnosis_code, claim_status from pg.dw.fct_claim where {PA_MEMBERS}",
    "fct_pharmacy_claim": f"""select pharmacy_claim_id, member_id, fill_date, drug_name, generic_name, days_supply,
                                     claim_status, is_paid, prior_authorization_request_id
                              from pg.dw.fct_pharmacy_claim where {PA_MEMBERS}""",
}


def postgres_dsn() -> str:
    env = {}
    env_path = os.path.join(REPO_ROOT, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    parts = {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", env.get("POSTGRES_DB", "aca_health")),
        "user": os.environ.get("PGUSER", env.get("POSTGRES_USER", "etl")),
        "password": os.environ.get("PGPASSWORD", env.get("POSTGRES_PASSWORD", "")),
    }
    return " ".join(f"{k}={v}" for k, v in parts.items())


def build(path: str = DB_PATH, copy_review: bool = True) -> None:
    tmp = path + ".tmp"
    for p in (tmp, tmp + ".wal"):
        if os.path.exists(p):
            os.remove(p)
    conn = duckdb.connect(tmp)
    conn.execute("install postgres; load postgres")
    conn.execute(f"attach '{postgres_dsn()}' as pg (type postgres, read_only)")

    conn.execute("create schema dw")
    for name, sql in TABLES.items():
        conn.execute(f"create table dw.{name} as {sql}")
        print(f"dw.{name}: {conn.execute(f'select count(*) from dw.{name}').fetchone()[0]} rows")

    conn.execute(REVIEW_DDL)
    if copy_review:
        # New decision_ids in the original order, so the sequence stays ahead of every row
        conn.execute("""
            insert into review.prior_authorization_decision
                (prior_authorization_request_id, decided_at, decided_by, outcome, reason, confidence,
                 policy_id, policy_version, model, checks, summary, np_rationale)
            select prior_authorization_request_id, decided_at, decided_by, outcome, reason, confidence,
                   policy_id, policy_version, model, checks::json, summary, np_rationale
            from pg.review.prior_authorization_decision
            order by decided_at, decision_id
        """)
        n = conn.execute("select count(*) from review.prior_authorization_decision").fetchone()[0]
        print(f"review.prior_authorization_decision: {n} rows")

    conn.execute("detach pg")
    conn.execute("checkpoint")
    conn.close()
    os.replace(tmp, path)
    print(f"Wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=DB_PATH)
    parser.add_argument("--no-review", action="store_true", help="do not copy the existing paper trail")
    args = parser.parse_args()
    build(args.out, copy_review=not args.no_review)


if __name__ == "__main__":
    main()
