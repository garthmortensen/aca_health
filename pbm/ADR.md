# Architecture decision records: prior authorization review

Date: 2026-11-11. All decisions below are accepted. Each was made step by step with the project owner; the "Why" is the reason given at the time.

## Background: what `demo.md` proposed

`pbm/demo.md` is the original plan for a demo aimed at a pharmacy data science role (see `description.md` and `linkedin_post.md`). Its idea, in brief:

- **Build a prior authorization reviewer.** Claude pulls structured facts from a clinical note (diagnosis, drugs already tried, lab values), the facts are matched against a coverage checklist, and the case is either approved automatically or sent to a human when confidence is low.
- **Use LangGraph** to wire the steps as a branching workflow.
- **Generate synthetic notes from known facts.** Faker cannot write clinical notes, but Claude can. Choosing the facts first gives an answer key, so the reviewer can be graded honestly.
- **Evaluate it:** precision and recall on approvals, extraction accuracy per field, whether confidence is trustworthy, and a messy batch (typos, missing fields).
- **Keep it safe:** synthetic notes only, never real patient text.

What we kept: the extract, match, decide flow, truth-first synthetic notes, and the synthetic-only rule. What we changed is recorded below (ADR 6 drops LangGraph, ADR 2 and 8 narrow the scope, and the evaluation work is archived for now).

---

## ADR 1: Pharmacy claims get their own fact table

**Context.** Pharmacy fills carry different fields from medical claims (drug code, days supply, refill number, reject codes) and are adjudicated by a pharmacy benefit manager. The original data had pharmacy rows mixed into medical claims with placeholder values.

**Decision.** Add `fct_pharmacy_claim`, `fct_prior_authorization_request`, and `dim_formulary`. Remove drug rows from the medical claims data.

**Why.** Separate grain, separate fields, and no double counting of cost per member per month.

**Consequences.** `agg_trend_descriptor`'s pharmacy bucket is now empty. Drug spend comes only from `fct_pharmacy_claim`.

## ADR 2: Narrow the policy to one drug class and three criteria

**Context.** The first pass had three policies and about fifteen facts. That was too much to understand and explain.

**Decision.** One policy, GLP-1 receptor agonists for type 2 diabetes, with three criteria: type 2 diabetes documented, age 18 or older, HbA1c 7.0% or higher.

**Why.** Small enough to hold in your head, and every criterion is checkable from a note.

**Consequences.** The historical `decision` column in `prior_authorization_requests` was labeled with the older six-criterion policy. Treat it as what the old process decided. Our system decides afresh.

## ADR 3: Policy and decision settings live in one YAML file

**Decision.** `pbm/config.yaml` holds the criteria, the near-threshold band, and the confidence floor. Extraction, the decision rule, and the dashboard all read from it.

**Why.** One place to change a rule, and the policy version recorded on every decision says which rules applied.

## ADR 4: The AI extracts, plain code decides

**Decision.** Claude is called once per note, in `extract.py`, and returns facts with verbatim quotes. `decide.py` applies the policy to those facts with no AI.

**Why.** The decision is explainable and rerunnable. Every criterion result points to a quote the reviewer can check.

**Consequences.** Extraction quality bounds decision quality. A null fact means "not documented", never a guess.

## ADR 5: Three outcomes, and the system never denies

**Decision.** Order of checks, strongest signal first:

1. Any criterion fails on a documented fact: **deny**. A reviewer signs it, with the failing criterion pre-filled.
2. A fact is missing, a value is near its threshold, or confidence is below the floor: **unclear**. A reviewer decides.
3. Otherwise: **approve**, decided by the system, with the quotes as the paper trail.

**Why.** A documented failure is a stronger signal than low confidence. Denials need a human signature.

## ADR 6: Plain Python, not LangGraph

**Context.** `demo.md` suggested LangGraph for the branching workflow.

**Decision.** Three small scripts run in order (`extract`, `decide`, `record`).

**Why.** There is one branch point, and the goal is for the owner to understand every step. A graph framework adds a concept without removing code.

## ADR 7: Near-threshold values go to a reviewer

**Decision.** HbA1c within 0.3 of 7.0 (6.7 to 7.3) is treated as unclear even when it passes. Age has no band.

**Why.** A 0.1 transcription error flips the decision at the threshold.

**Consequences.** Lower automation, higher safety. The band is a guess and lives in `config.yaml`.

## ADR 8: One overall confidence number, floor 0.9

**Decision.** The AI reports one confidence from 0 to 1. Below 0.9, the case is unclear. The floor is in `config.yaml`.

**Why.** Simple to explain and tune. A per-criterion flag would be more informative on screen but harder to reason about.

**Consequences.** The 0.9 floor is untested. It is a starting point to tune against reviewer behavior.

## ADR 9: Append-only paper trail in a separate `review` schema

**Decision.** `review.prior_authorization_decision` holds one row per decision event, from the system or from a reviewer, never updated or deleted. A view returns the latest row per request. The schema is separate from `dw` and `summary`.

**Why.** Each row records who decided, when, which policy version and AI model, and the quote behind each criterion. The history of a request is the sequence of its rows. Keeping it apart from the dbt-managed warehouse means a rebuild never touches it and the warehouse stays read-only for the application.

## ADR 10: Reviewer outcomes are approve, deny, or request more information

**Decision.** Reviewers choose one of the three and must write a rationale.

**Why.** Requesting more information from the prescriber is a common real outcome, and it is different from a denial.

## ADR 11: A Streamlit dashboard for the reviewer

**Decision.** Full-width queue with an outcome dropdown filter, sorted by AI confidence descending. The selected case appears below it with the AI assessment, quotes, note, history, and decision form. The queue includes approved cases, so the paper trail is browsable.

**Why.** It lets a nurse practitioner work unclear cases while clear cases remain documented and auditable.

## ADR 12: Spell everything out, no shorthand

**Decision.** Names use full words (`prior_authorization_request`, `hba1c_percent`, `has_type2_diabetes_diagnosis`). Request ID values keep their `PA` prefix as identifiers, like `MBR` and `PRV`.

**Why.** The owner is learning the domain, and readability beats brevity.

---

## Not decided yet

- Whether to add a dbt model over the decision log (automation rate, reviewer agreement with the AI, turnaround).
- Whether reviewers should get a different rationale prompt when they override a system approval.
- Whether to bring back an evaluation of the reviewer against the answer key. The first-pass version is on branch `archive/pbm-v1`.
- Whether to rename the `pbm/` folder, since `pbm` itself is shorthand.
