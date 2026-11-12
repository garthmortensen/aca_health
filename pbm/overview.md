# Prior authorization review: overview

A **prior authorization** is the plan's approval that a prescriber must get before certain drugs are covered. This system reads the prescriber's clinical note, checks it against the coverage policy, approves clear cases with a paper trail, and sends everything else to a nurse practitioner (NP) in a dashboard.

Everything here uses synthetic data. The diagrams follow the [C4 model](https://c4model.com): each level zooms into one box of the level above.

| Level | Question it answers |
|---|---|
| 1. Context | Who and what does the system touch? |
| 2. Containers | What are the runnable pieces and where does data live? |
| 3. Components | What are the steps inside the review pipeline? |
| 4. Dynamic | What happens, in order, for one request? |

Supporting diagrams: the decision rule, and the paper trail table.

---

## 1. System context

```mermaid
C4Context
    title System context: prior authorization review

    Person(prescriber, "Prescriber", "Writes the clinical note and requests a drug that needs prior authorization")
    Person(np, "Nurse practitioner", "Reviews unclear and failing cases, signs the final decision")

    System(review, "Prior authorization review", "Reads the note, checks it against the coverage policy, approves clear cases, routes the rest to a reviewer, records everything")

    System_Ext(claude, "Claude API (Anthropic)", "Reads a clinical note and returns the facts the policy asks about, with quotes")

    Rel(prescriber, review, "Submits clinical note")
    Rel(review, claude, "Sends note, receives facts, quotes, confidence", "HTTPS")
    Rel(np, review, "Reviews queue, records decision and rationale")
```

The prescriber is shown for completeness. In this demo the notes are synthetic files, not a live feed.

---

## 2. Containers

```mermaid
C4Container
    title Containers: prior authorization review

    Person(np, "Nurse practitioner", "Reviews unclear and failing cases")
    System_Ext(claude, "Claude API", "Anthropic")

    System_Boundary(sys, "Prior authorization review") {
        Container(config, "config.yaml", "YAML", "The policy (criteria, thresholds) and the confidence floor. The only place rules live")
        Container(notes, "Clinical notes", "JSONL file", "Synthetic notes, one per request, with the facts each was written from")
        Container(pipeline, "Review pipeline", "Python: extract, decide, record", "Turns a note into a decision and writes it to the paper trail")
        Container(app, "Reviewer dashboard", "Streamlit", "Queue, case detail, decision form")
        ContainerDb(review_db, "review schema", "PostgreSQL", "Append-only decision log and current-status view")
    }

    System_Boundary(wh, "Warehouse (built earlier)") {
        Container(gen, "Seed data generator", "Python + scenarios.json", "Generates members, claims, pharmacy claims, prior authorization requests, formulary")
        Container(dbt, "dbt project", "dbt-postgres", "Loads seeds, builds staging, dw, summary")
        ContainerDb(warehouse, "dw and summary schemas", "PostgreSQL", "fct_prior_authorization_request, fct_pharmacy_claim, dim_formulary, aggregates")
    }

    Rel(gen, dbt, "Writes CSV seeds")
    Rel(dbt, warehouse, "Loads and transforms")

    Rel(pipeline, notes, "Reads")
    Rel(pipeline, config, "Reads policy and threshold")
    Rel(pipeline, claude, "Extracts facts from each note", "HTTPS")
    Rel(pipeline, review_db, "Appends system decisions", "SQL")

    Rel(app, config, "Reads criteria for the sidebar")
    Rel(app, review_db, "Reads queue and history, appends reviewer decisions", "SQL")
    Rel(app, warehouse, "Reads drug, member, prescriber, date for each request", "SQL")
    Rel(app, notes, "Shows the note for the selected case")
    Rel(np, app, "Filters, selects a case, decides", "Browser")
```

Two databases' worth of schemas live in one PostgreSQL instance (`aca_health`). They are drawn separately because they are managed differently: `dw` and `summary` are rebuilt by dbt, while `review` is written by the application and never rebuilt.

---

## 3. Components: the review pipeline

```mermaid
C4Component
    title Components: review pipeline

    Container_Ext(config, "config.yaml", "YAML", "Policy and confidence floor")
    Container_Ext(notes, "Clinical notes", "JSONL", "Input")
    System_Ext(claude, "Claude API", "Anthropic")
    ContainerDb_Ext(review_db, "review schema", "PostgreSQL", "Paper trail")

    Container_Boundary(pipe, "Review pipeline (pbm/)") {
        Component(extract, "extract.py", "Python, Pydantic", "One Claude call per note. Returns diagnosis, age, HbA1c, a quote for each, and one confidence number. Null means not documented")
        Component(decide, "decide.py", "Python, no AI", "Applies the policy to the facts. Per criterion: pass, fail, or unknown. Then the outcome")
        Component(record, "record.py", "Python, psycopg", "write_system_decisions loads decisions. write_np_decision appends one reviewer row")
        Component(ex_file, "extractions.jsonl", "File", "Facts, quotes, confidence, model, token usage")
        Component(dec_file, "decisions.jsonl", "File", "Outcome, reason, per-criterion checks, policy version")
    }

    Rel(extract, notes, "Reads")
    Rel(extract, config, "Reads criteria to build the question list")
    Rel(extract, claude, "Sends note and questions", "HTTPS")
    Rel(extract, ex_file, "Writes")
    Rel(decide, ex_file, "Reads")
    Rel(decide, config, "Reads criteria, thresholds, confidence floor")
    Rel(decide, dec_file, "Writes")
    Rel(record, dec_file, "Reads")
    Rel(record, review_db, "Appends rows", "SQL")
```

Run in order: `python -m pbm.extract`, then `python -m pbm.decide`, then `python -m pbm.record`. The AI is used in exactly one place, `extract.py`. Everything after it is plain code that anyone can read and rerun.

---

## 4. Dynamic: one request, end to end

```mermaid
C4Dynamic
    title Dynamic: one request from note to recorded decision

    Person(np, "Nurse practitioner", "")
    Container(extract, "extract.py", "Python", "")
    Container(decide, "decide.py", "Python", "")
    Container(record, "record.py", "Python", "")
    System_Ext(claude, "Claude API", "")
    ContainerDb(review_db, "review schema", "PostgreSQL", "")
    Container(app, "Reviewer dashboard", "Streamlit", "")

    Rel(extract, claude, "1. Note plus the policy's questions")
    Rel(claude, extract, "2. Facts, quotes, confidence")
    Rel(decide, decide, "3. Check each criterion, then pick approve, deny, or unclear")
    Rel(record, review_db, "4. Append a system row (decided_by = system)")
    Rel(app, review_db, "5. Show non-approved cases, highest confidence first")
    Rel(np, app, "6. Open case, read quotes and note, choose outcome, write rationale")
    Rel(app, review_db, "7. Append a reviewer row (decided_by = reviewer name)")
```

Nothing is ever updated or deleted. A request's status is simply its latest row, and its history is all of its rows in order.

---

## Supporting: the decision rule

The rule lives in `decide.py` and is configured in `config.yaml`. Strongest signal first:

```mermaid
flowchart TD
    A[Facts and quotes from the note] --> B{Any criterion fails<br/>on a documented fact?}
    B -- yes --> DENY[deny<br/>reviewer signs, failing criterion pre-filled]
    B -- no --> C{Any fact missing<br/>from the note?}
    C -- yes --> UNCLEAR[unclear<br/>reviewer decides]
    C -- no --> D{Any value near<br/>its threshold?<br/>HbA1c within 0.3 of 7.0}
    D -- yes --> UNCLEAR
    D -- no --> E{AI confidence below<br/>the floor? 0.9}
    E -- yes --> UNCLEAR
    E -- no --> APPROVE[approve<br/>system decides, quotes are the paper trail]

    DENY --> F[Reviewer outcome:<br/>approve, deny, or request more info]
    UNCLEAR --> F
```

The policy has three criteria: type 2 diabetes documented, age 18 or older, HbA1c 7.0% or higher. The system never denies on its own. A reviewer signs every deny, and every case that is not a clear approval.

---

## Supporting: the paper trail

One table, one row per decision event, never updated.

```mermaid
erDiagram
    PRIOR_AUTHORIZATION_REQUEST ||--o{ DECISION : "has history of"

    PRIOR_AUTHORIZATION_REQUEST {
        text prior_authorization_request_id PK
        text member_id
        text drug_name
        date request_date
        text prescriber_specialty
    }

    DECISION {
        bigint decision_id PK
        text prior_authorization_request_id FK
        timestamptz decided_at
        text decided_by "system or the reviewer's name"
        text outcome "approve, deny, unclear, request_more_info"
        text reason "one human-readable line"
        numeric confidence "AI confidence, system rows only"
        text policy_id
        text policy_version "which rules applied"
        text model "which AI model read the note"
        jsonb checks "per criterion: status, value, quote"
        text np_rationale "reviewer free text, reviewer rows only"
    }
```

`PRIOR_AUTHORIZATION_REQUEST` is `dw.fct_prior_authorization_request`. `DECISION` is `review.prior_authorization_decision`. The view `review.prior_authorization_status` returns the latest decision per request, which is what the dashboard queue shows.

---

## Where each piece lives

| Piece | Location |
|---|---|
| Policy and decision settings | `pbm/config.yaml` |
| Fact extraction (Claude) | `pbm/extract.py` |
| Decision rule | `pbm/decide.py` |
| Paper trail writers | `pbm/record.py` |
| Reviewer dashboard | `pbm/app.py` (run from the repo root: `streamlit run pbm/app.py`) |
| Paper trail table and view | `infrastructure/sql/ddl/06_review_schema.sql` |
| Synthetic notes | `pbm/data/notes.jsonl` |
| Warehouse models | `transform/models/` (`fct_prior_authorization_request`, `fct_pharmacy_claim`, `dim_formulary`) |
| First-pass pipeline (archived) | git branch `archive/pbm-v1` |
