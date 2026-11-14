"""Step 2: check each criterion against two sources, then decide. No AI here.

Every criterion is checked twice:
  warehouse   facts from the database (pbm/warehouse.py)
  note        facts the AI read from the clinical note (pbm/extract.py)

A criterion's status is pass, fail, near (a lab slightly below its minimum, within the
criterion's tolerance), unknown (neither source knows), or conflict (the two sources
disagree). Each decision carries, per criterion,
both values and the evidence behind each. That record is the paper trail.

Usage:
  python -m pbm.decide                 # all -> pbm/data/decisions.jsonl
"""
from __future__ import annotations

import argparse
import json
import os

import yaml

from pbm import warehouse

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))
POLICY, DECISION = CONFIG["policy"], CONFIG["decision"]
IN_PATH = os.path.join(HERE, "data", "extractions.jsonl")
OUT_PATH = os.path.join(HERE, "data", "decisions.jsonl")


def status(criterion: dict, value) -> str:
    """One value against one criterion."""
    if value is None:
        return "unknown"
    if "pass_when" in criterion:
        return "pass" if value == criterion["pass_when"] else "fail"
    if value >= criterion["min"]:
        return "pass"
    # Below the minimum. Within the tolerance it is a near miss the reviewer may approve; there is no band above
    return "near" if round(criterion["min"] - value, 6) <= criterion.get("tolerance", 0) else "fail"


def shortfall(criterion: dict, sources: dict) -> str | None:
    """The line for the reviewer when a lab is below its minimum but within tolerance, else None."""
    parts = [f"{name} {s['value']} ({round(criterion['min'] - s['value'], 6):g} below)"
             for name, s in sources.items() if s["status"] == "near"]
    if not parts:
        return None
    return (f"{criterion.get('short', criterion['id'])}: " + ", ".join(parts)
            + f", within the {criterion['tolerance']:g} tolerance")


def check(criterion: dict, note_facts: dict, warehouse_facts: dict) -> dict:
    """One criterion against both sources."""
    fact = criterion["fact"]
    from_warehouse = warehouse_facts.get(fact, {})
    quote = next((q["text"] for q in note_facts.get("quotes", []) if q["fact"] == fact), None)
    sources = {
        "warehouse": {"value": from_warehouse.get("value"), "evidence": from_warehouse.get("evidence")},
        "note": {"value": note_facts.get(fact), "evidence": quote},
    }
    for source in sources.values():
        source["status"] = status(criterion, source["value"])

    known = {s["status"] for s in sources.values()} - {"unknown"}
    if len(known) == 2:
        overall = "conflict"          # one source passes, the other fails
    elif known:
        overall = known.pop()         # the sources agree, or only one of them knows
    else:
        overall = "unknown"
    return {"id": criterion["id"], "question": criterion["question"], "status": overall,
            "shortfall": shortfall(criterion, sources), **sources}


def describe(c: dict) -> str:
    return f"{c['question']} (warehouse: {c['warehouse']['value']}, note: {c['note']['value']})"


def decide(extraction: dict, warehouse_facts: dict) -> dict:
    """The decision rule from config.yaml, strongest signal first."""
    note_facts = extraction.get("facts") or {}
    confidence = note_facts.get("confidence")
    checks = [check(c, note_facts, warehouse_facts) for c in POLICY["criteria"]]

    def having(status):
        return [c for c in checks if c["status"] == status]

    floor = DECISION["confidence_threshold"]
    if having("fail"):
        outcome, reason = "deny", "Fails: " + "; ".join(map(describe, having("fail")))
    elif having("conflict"):
        outcome, reason = "unclear", "Sources disagree: " + "; ".join(map(describe, having("conflict")))
    elif having("unknown"):
        outcome, reason = "unclear", "Not found in warehouse or note: " + "; ".join(c["question"] for c in having("unknown"))
    elif having("near"):
        outcome, reason = "unclear", "Below the minimum, within tolerance: " + "; ".join(c["shortfall"] for c in having("near"))
    elif all(c["warehouse"]["status"] == "pass" for c in checks):
        # The warehouse alone meets every criterion, so the AI's confidence does not gate the approval.
        # A weak reading of the note is recorded in the reason, and the dashboard lists it as an AI flag.
        outcome, reason = "approve", "All criteria met in the warehouse"
        if confidence is None:
            reason += "; AI flag: the AI could not read the note"
        elif confidence < floor:
            reason += f"; AI flag: confidence {confidence} below {floor}"
    elif confidence is None:
        outcome, reason = "unclear", "AI could not read the note"
    elif confidence < floor:
        outcome, reason = "unclear", f"AI confidence {confidence} below {floor}"
    else:
        outcome, reason = "approve", "All criteria met"

    return {"outcome": outcome, "reason": reason, "confidence": confidence, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="inp", default=IN_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    extractions = [json.loads(line) for line in open(args.inp)]
    warehouse_facts = warehouse.lookup([e["prior_authorization_request_id"] for e in extractions])

    with open(args.out, "w") as f:
        for e in extractions:
            request_id = e["prior_authorization_request_id"]
            d = decide(e, warehouse_facts.get(request_id, {}))
            record = {
                "prior_authorization_request_id": request_id,
                "policy_id": POLICY["id"],
                "policy_version": POLICY["version"],
                "model": e.get("model"),
                "decided_by": "system" if d["outcome"] == "approve" else "pending_np_review",
                **d,
            }
            f.write(json.dumps(record) + "\n")

            print(f"\n{request_id}  {d['outcome'].upper():8} {d['reason']}")
            for c in d["checks"]:
                print(f"   {c['status']:8} {c['question']:52} warehouse={c['warehouse']['value']!s:6} note={c['note']['value']!s:6}")
    print(f"\nWrote {len(extractions)} decisions to {args.out}")


if __name__ == "__main__":
    main()
