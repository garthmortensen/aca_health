"""Step 2: check each criterion against two sources, then decide. No AI here.

Every criterion is checked twice:
  warehouse   facts from the database (pbm/warehouse.py)
  note        facts the AI read from the clinical note (pbm/extract.py)

A criterion's status is pass, fail, unknown (neither source knows), or
conflict (the two sources disagree). Each decision carries, per criterion,
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
    return "pass" if value >= criterion["min"] else "fail"


def is_near(criterion: dict, value) -> bool:
    """True when a lab value is within the criterion's tolerance of its threshold, above or below."""
    return value is not None and "tolerance" in criterion and round(abs(value - criterion["min"]), 6) <= criterion["tolerance"]


def fyi(criterion: dict, sources: dict) -> str | None:
    """The FYI line for the NP when a lab is within tolerance of its threshold, else None."""
    near = {name: s["value"] for name, s in sources.items() if is_near(criterion, s["value"])}
    if not near:
        return None
    parts = []
    for name, value in near.items():
        gap = round(abs(value - criterion["min"]), 6)
        parts.append(f"{name} {value} ({'at' if gap == 0 else f'{gap:g} ' + ('below' if value < criterion['min'] else 'above')})")
    label = criterion.get("label", criterion["id"])
    return f"{label} is within {criterion['tolerance']:g} of the {criterion['min']:g} minimum: " + ", ".join(parts)


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
    note = fyi(criterion, sources)
    return {"id": criterion["id"], "question": criterion["question"], "status": overall,
            "near": note is not None, "fyi": note, **sources}


def describe(c: dict) -> str:
    return f"{c['question']} (warehouse: {c['warehouse']['value']}, note: {c['note']['value']})"


def decide(extraction: dict, warehouse_facts: dict) -> dict:
    """The decision rule from config.yaml, strongest signal first."""
    note_facts = extraction.get("facts") or {}
    confidence = note_facts.get("confidence")
    checks = [check(c, note_facts, warehouse_facts) for c in POLICY["criteria"]]

    def having(key, value=True):
        return [c for c in checks if c[key] == value]

    if having("status", "fail"):
        outcome, reason = "deny", "Fails: " + "; ".join(map(describe, having("status", "fail")))
    elif having("status", "conflict"):
        outcome, reason = "unclear", "Sources disagree: " + "; ".join(map(describe, having("status", "conflict")))
    elif having("status", "unknown"):
        outcome, reason = "unclear", "Not found in warehouse or note: " + "; ".join(c["question"] for c in having("status", "unknown"))
    elif having("near"):
        outcome, reason = "unclear", "Within lab tolerance: " + "; ".join(map(describe, having("near")))
    elif confidence is None:
        outcome, reason = "unclear", "AI could not read the note"
    elif confidence < DECISION["confidence_threshold"]:
        outcome, reason = "unclear", f"AI confidence {confidence} below {DECISION['confidence_threshold']}"
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
