"""Step 3: turn extracted facts into a decision, criterion by criterion.

No AI here. This is the policy in config.yaml applied to the facts from step 2.
Every decision carries, for each criterion: pass / fail / unknown, the value,
and the quote behind it. That record is the paper trail.

Usage:
  python -m pbm.decide --in pbm/data/extractions_sample.jsonl   # try the sample
  python -m pbm.decide                                           # all -> pbm/data/decisions.jsonl
"""
from __future__ import annotations

import argparse
import json
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))
POLICY, DECISION = CONFIG["policy"], CONFIG["decision"]
IN_PATH = os.path.join(HERE, "data", "extractions.jsonl")
OUT_PATH = os.path.join(HERE, "data", "decisions.jsonl")
NOTES_PATH = os.path.join(HERE, "data", "notes.jsonl")


def check(criterion: dict, facts: dict) -> dict:
    """One criterion against the facts: pass, fail, or unknown (not documented)."""
    value = facts.get(criterion["fact"])
    quote = next((q["text"] for q in facts.get("quotes", []) if q["fact"] == criterion["fact"]), None)
    result = {"id": criterion["id"], "question": criterion["question"], "value": value, "quote": quote, "near": False}
    if value is None:
        result["status"] = "unknown"
    elif "pass_when" in criterion:
        result["status"] = "pass" if value == criterion["pass_when"] else "fail"
    else:
        result["status"] = "pass" if value >= criterion["min"] else "fail"
        if "near" in criterion:
            result["near"] = round(abs(value - criterion["min"]), 6) < criterion["near"]
    return result


def decide(extraction: dict) -> dict:
    """The decision rule from config.yaml, strongest signal first."""
    facts = extraction.get("facts")
    if not facts:
        return {"outcome": "unclear", "reason": "AI could not read the note", "checks": [], "confidence": None}

    checks = [check(c, facts) for c in POLICY["criteria"]]
    confidence = facts["confidence"]
    failed = [c for c in checks if c["status"] == "fail"]
    unknown = [c for c in checks if c["status"] == "unknown"]
    near = [c for c in checks if c["near"]]

    if failed:
        outcome, reason = "deny", "Fails: " + "; ".join(f"{c['question']} ({c['value']})" for c in failed)
    elif unknown:
        outcome, reason = "unclear", "Not documented: " + "; ".join(c["question"] for c in unknown)
    elif near:
        outcome, reason = "unclear", "Near threshold: " + "; ".join(f"{c['question']} ({c['value']})" for c in near)
    elif confidence < DECISION["confidence_threshold"]:
        outcome, reason = "unclear", f"AI confidence {confidence} below {DECISION['confidence_threshold']}"
    else:
        outcome, reason = "approve", "All criteria met on documented facts"

    return {"outcome": outcome, "reason": reason, "confidence": confidence, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="inp", default=IN_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    extractions = [json.loads(line) for line in open(args.inp)]
    truth = {n["prior_authorization_request_id"]: n for n in map(json.loads, open(NOTES_PATH))}

    with open(args.out, "w") as f:
        for e in extractions:
            d = decide(e)
            record = {
                "prior_authorization_request_id": e["prior_authorization_request_id"],
                "policy_id": POLICY["id"],
                "policy_version": POLICY["version"],
                "model": e.get("model"),
                "decided_by": "system" if d["outcome"] == "approve" else "pending_np_review",
                **d,
            }
            f.write(json.dumps(record) + "\n")

            # Show it next to the facts the note was written from
            t = truth[e["prior_authorization_request_id"]]
            print(f"\n{record['prior_authorization_request_id']}  {d['outcome'].upper():8} {d['reason']}")
            for c in d["checks"]:
                print(f"   {c['status']:8} {c['question']:48} value={c['value']!s:6} quote: {(c['quote'] or '')[:60]}")
            print(f"   confidence={d['confidence']}   (note written with: {', '.join(f'{k}={t['truth'].get(k)}' for k in [c['fact'] for c in POLICY['criteria']])})")
    print(f"\nWrote {len(extractions)} decisions to {args.out}")


if __name__ == "__main__":
    main()
