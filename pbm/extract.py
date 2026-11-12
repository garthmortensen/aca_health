"""Step 2: read a clinical note, return the facts the policy asks about.

One Claude call per note. The output is a validated object (see Facts below):
each fact is either a value with a verbatim quote from the note, or null when
the note does not say. One overall confidence number, 0 to 1.

Usage:
  python -m pbm.extract --limit 3      # try a few, print next to the known truth
  python -m pbm.extract                # all notes -> pbm/data/extractions.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import anthropic
import yaml
from pydantic import BaseModel, Field

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))["policy"]
NOTES_PATH = os.path.join(HERE, "data", "notes.jsonl")
OUT_PATH = os.path.join(HERE, "data", "extractions.jsonl")
MODEL = "claude-opus-5-5"


class Quote(BaseModel):
    fact: str = Field(description="Which fact this quote supports")
    text: str = Field(description="Verbatim words from the note")


class Facts(BaseModel):
    """What the GLP-1 policy needs to know. Null means the note does not say."""
    has_type2_diabetes_diagnosis: Optional[bool] = Field(
        description="True if type 2 diabetes is documented as a diagnosis. False if the note says "
                    "prediabetes or no diabetes. Null if the note does not address it.")
    age: Optional[int] = Field(
        description="Age in years, from a stated age or from date of birth and the note date.")
    hba1c_percent: Optional[float] = Field(
        description="Most recent HbA1c in percent, copied exactly as written.")
    quotes: List[Quote] = Field(description="One verbatim quote per non-null fact")
    confidence: float = Field(
        description="0 to 1. How sure you are that every non-null fact is right and every null fact "
                    "is truly absent from the note. Lower it for ambiguity, contradictions, or illegible text.")


SYSTEM = (
    "You extract facts from clinical notes for a prior authorization review. "
    "Report only what the note documents. If a fact is not stated, return null for it; never fill in a "
    "typical value. Quote the note for every fact you report. Copy numbers exactly."
)


def extract(note: str, client: anthropic.Anthropic) -> dict:
    """Return the facts as a plain dict, plus the model's stop reason and token usage."""
    questions = "\n".join(f"- {c['question']}" for c in POLICY["criteria"])
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"The policy asks:\n{questions}\n\nNOTE:\n{note}"}],
        output_format=Facts,
    )
    facts = response.parsed_output.model_dump() if response.parsed_output else None
    return {
        "facts": facts,
        "stop_reason": response.stop_reason,
        "model": response.model,
        "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="Only the first N notes")
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    notes = [json.loads(line) for line in open(NOTES_PATH)]
    # Only GLP-1 for type 2 diabetes requests: that is the policy we wrote
    notes = [n for n in notes if n["policy_id"] == POLICY["id"] and n.get("note")]
    if args.limit:
        notes = notes[: args.limit]

    client = anthropic.Anthropic(max_retries=3)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: extract(n["note"], client), notes))

    with open(args.out, "w") as f:
        for note, result in zip(notes, results):
            record = {"prior_authorization_request_id": note["prior_authorization_request_id"], "style": note["style"], **result}
            f.write(json.dumps(record) + "\n")

    # Show what came back next to the facts the note was written from
    fact_names = [c["fact"] for c in POLICY["criteria"]]
    for note, result in zip(notes, results):
        print(f"\n{note['prior_authorization_request_id']}  ({note['style']} note, omitted on purpose: {note['omitted_fields'] or 'nothing'})")
        facts = result["facts"] or {}
        for name in fact_names:
            truth = None if name in note["omitted_fields"] else note["truth"].get(name)
            quote = next((q["text"] for q in facts.get("quotes", []) if q["fact"] == name), "")
            print(f"  {name:32} truth={truth!s:6} got={facts.get(name)!s:6}  quote: {quote[:70]}")
        print(f"  confidence={facts.get('confidence')}  tokens={result['usage']}")
    print(f"\nWrote {len(notes)} extractions to {args.out}")


if __name__ == "__main__":
    main()
