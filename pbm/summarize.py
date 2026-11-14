"""Step 3: write a short briefing for the nurse practitioner. One Claude call per case.

Only cases that go to a reviewer get one (outcome deny or unclear). The briefing
says what the warehouse shows, what the note says, where they disagree, and what
is missing. It never recommends approve or deny: that is the reviewer's call.

The briefing is added to each decision in pbm/data/decisions.jsonl as "summary".

Usage:
  python -m pbm.summarize --limit 3    # try a few and print them
  python -m pbm.summarize              # every case that needs a reviewer
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor

import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
DECISIONS_PATH = os.path.join(HERE, "data", "decisions.jsonl")
NOTES_PATH = os.path.join(HERE, "data", "notes.jsonl")
MODEL = "claude-opus-5-5"

SYSTEM = (
    "You brief a nurse practitioner who is about to review a prior authorization request. "
    "You are given the policy checks, each with a value from the claims warehouse and a value the AI read "
    "from the clinical note, the note itself, and for any lab slightly below its minimum but within "
    "tolerance a 'shortfall' line.\n\n"
    "Write at most five short bullet points, under 90 words in total, plain text:\n"
    "- lead with any criterion where the warehouse and the note disagree, giving both values "
    "(skip this bullet when nothing disagrees)\n"
    "- then every 'shortfall' line, restated briefly: how far below the minimum the lab value is\n"
    "- then anything missing or failing\n"
    "- then anything in the note that bears on those points, such as a documented intolerance\n"
    "- say in one bullet which criteria are met by both sources\n\n"
    "Give evidence for and against evenly. Do not recommend, suggest, or imply an outcome: no "
    "'approve', 'deny', 'should', 'appears to qualify', or similar. The reviewer decides."
)


def summarize(decision: dict, note: str, client: anthropic.Anthropic) -> str | None:
    """Return the briefing, or None if the model did not produce one."""
    checks = json.dumps(decision["checks"], indent=2)
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"CHECKS:\n{checks}\n\nNOTE:\n{note}"}],
        output_config={"effort": "low"},
        # If the model declines a request, the API retries it on a fallback model
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason != "end_turn":
        return None
    return "".join(block.text for block in response.content if block.type == "text").strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="Only the first N cases that need a reviewer")
    parser.add_argument("--path", default=DECISIONS_PATH)
    args = parser.parse_args()

    decisions = [json.loads(line) for line in open(args.path)]
    notes = {n["prior_authorization_request_id"]: n["note"] for n in map(json.loads, open(NOTES_PATH))}
    for_review = [d for d in decisions if d["outcome"] != "approve"][: args.limit]

    client = anthropic.Anthropic(max_retries=3)
    with ThreadPoolExecutor(max_workers=6) as pool:
        summaries = list(pool.map(
            lambda d: summarize(d, notes[d["prior_authorization_request_id"]], client), for_review))

    for decision, summary in zip(for_review, summaries):
        decision["summary"] = summary
        print(f"\n{decision['prior_authorization_request_id']}  {decision['outcome'].upper()}\n{summary}")

    with open(args.path, "w") as f:
        for decision in decisions:
            f.write(json.dumps(decision) + "\n")
    print(f"\nAdded {sum(s is not None for s in summaries)} summaries to {args.path}")


if __name__ == "__main__":
    main()
