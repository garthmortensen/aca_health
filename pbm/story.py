"""Step 3b: tell the story of the clinical note, so the reviewer starts with the context.

One Claude call per case under the configured policy. It reads the note (and the request's drug, date and prescriber
specialty) and writes a short narrative: who the patient is, how the diabetes has been
managed, what the latest labs show, and what the prescriber is asking for. It does not
check the policy, compare sources, or recommend anything. That is the briefing's job
(summarize.py), and the decision rule's.

Stories describe the note, not the decision, so they are written once per case and
kept in pbm/data/stories.jsonl, which the dashboard reads. Cases that already have a
story are skipped unless --force is given.

Usage:
  python -m pbm.story                  # a story for every case that does not have one
  python -m pbm.story --limit 3        # only the first 3 such cases
  python -m pbm.story --force          # rewrite every story
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor

import anthropic
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_PATH = os.path.join(HERE, "data", "notes.jsonl")
STORIES_PATH = os.path.join(HERE, "data", "stories.jsonl")
POLICY_ID = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))["policy"]["id"]
MODEL = "claude-opus-5-5"

SYSTEM = (
    "You help a nurse practitioner who is about to review a prior authorization request. "
    "You are given the clinical note that came with the request, and the drug, date and prescriber "
    "specialty of the request. Tell the story of the case so the reviewer understands the starting "
    "context before looking at any checks.\n\n"
    "Write one short paragraph of plain prose, 80 to 120 words, in this order:\n"
    "- who the patient is (age, sex) and the diabetes history\n"
    "- how it has been managed so far: the medicines, for how long, how well they were tolerated\n"
    "- where things stand now: the latest labs and any symptoms or findings the note stresses\n"
    "- what the prescriber is asking for\n\n"
    "Use only what the note says. If the note is silent on something that matters to the story, say "
    "the note does not mention it. Give dates and numbers as written. Do not invent details, do not "
    "check anything against a policy, and do not recommend, suggest, or imply an outcome: no 'approve', "
    "'deny', 'should', 'meets', 'qualifies', or similar. No headings, no bullets, no patient name."
)


def story(note: dict, client: anthropic.Anthropic) -> str | None:
    """Return the story, or None if the model did not produce one."""
    # Only the note and the request's own facts go to the model, never the stored answer key
    context = (f"REQUEST: {note['drug_name']}, requested {note['request_date']}, "
               f"prescriber specialty {note['prescriber_specialty']}\n\nNOTE:\n{note['note']}")
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": context}],
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
    parser.add_argument("--limit", type=int, default=None, help="Only the first N cases that need a story")
    parser.add_argument("--force", action="store_true", help="Rewrite stories that already exist")
    parser.add_argument("--path", default=STORIES_PATH)
    args = parser.parse_args()

    notes = [n for n in map(json.loads, open(NOTES_PATH)) if n["policy_id"] == POLICY_ID]  # the cases in the queue
    stories = {}
    if os.path.exists(args.path) and not args.force:
        stories = {s["prior_authorization_request_id"]: s for s in map(json.loads, open(args.path))}
    todo = [n for n in notes if n["prior_authorization_request_id"] not in stories][: args.limit]

    client = anthropic.Anthropic(max_retries=3)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: story(n, client), todo))

    for note, text in zip(todo, results):
        request_id = note["prior_authorization_request_id"]
        if text:
            stories[request_id] = {"prior_authorization_request_id": request_id, "story": text, "model": MODEL}
        print(f"\n{request_id}\n{text}")

    with open(args.path, "w") as f:
        for s in stories.values():
            f.write(json.dumps(s) + "\n")
    print(f"\nWrote {sum(r is not None for r in results)} stories; {len(stories)} in {args.path}")


if __name__ == "__main__":
    main()
