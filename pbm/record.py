"""Step 4: write decisions to the paper trail, review.prior_authorization_decision.

Two writers:
  write_system_decisions(path)   load the rows produced by decide.py
  write_np_decision(...)         one row from the dashboard when a reviewer acts

Rows are only ever appended. The table lives in the app's DuckDB file (pbm/db.py).

Usage:
  python -m pbm.record                 # load pbm/data/decisions.jsonl
"""
from __future__ import annotations

import argparse
import json
import os

from pbm.db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
DECISIONS_PATH = os.path.join(HERE, "data", "decisions.jsonl")

INSERT = """
insert into review.prior_authorization_decision
    (prior_authorization_request_id, decided_by, outcome, reason, confidence,
     policy_id, policy_version, model, checks, summary, np_rationale)
values ($request_id, $decided_by, $outcome, $reason, $confidence,
        $policy_id, $policy_version, $model, $checks, $summary, $np_rationale)
"""


def write_system_decisions(path: str = DECISIONS_PATH) -> int:
    """Append every decision in the file as a 'system' row. Returns rows written."""
    decisions = [json.loads(line) for line in open(path)]
    with connect() as conn:
        for d in decisions:
            conn.execute(INSERT, {
                "request_id": d["prior_authorization_request_id"],
                "decided_by": "system",
                "outcome": d["outcome"],
                "reason": d["reason"],
                "confidence": d.get("confidence"),
                "policy_id": d.get("policy_id"),
                "policy_version": d.get("policy_version"),
                "model": d.get("model"),
                "checks": json.dumps(d.get("checks", [])),
                "summary": d.get("summary"),
                "np_rationale": None,
            })
    return len(decisions)


def write_np_decision(request_id: str, outcome: str, rationale: str, decided_by: str,
                      policy_id: str, policy_version: str) -> None:
    """Append one row for a human reviewer's action."""
    assert outcome in ("approve", "deny", "request_more_info"), outcome
    with connect() as conn:
        conn.execute(INSERT, {
            "request_id": request_id,
            "decided_by": decided_by,
            "outcome": outcome,
            "reason": f"Reviewed by {decided_by}",
            "confidence": None,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "model": None,
            "checks": None,
            "summary": None,
            "np_rationale": rationale,
        })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="inp", default=DECISIONS_PATH)
    args = parser.parse_args()
    n = write_system_decisions(args.inp)
    print(f"Appended {n} system decisions to review.prior_authorization_decision")


if __name__ == "__main__":
    main()
