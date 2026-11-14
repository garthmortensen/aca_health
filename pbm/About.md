# About: prior authorization review

This project checks prior authorization requests for GLP-1 drugs against a coverage policy. Plain code decides the clear cases and a nurse practitioner (NP) decides the rest. The AI reads clinical notes into facts and writes summaries for the NP, but never decides until its performance has been validated. All data is synthetic.

---

## 1. The pipeline: deterministic steps vs LLM calls

```mermaid
flowchart LR
    note["Clinical note<br/>(free text)"]
    wh[("Claims warehouse")]

    extract["extract.py<br/>LLM CALL 1<br/>facts + quotes + confidence"]
    lookup["warehouse.py<br/>SQL lookup<br/>no AI"]
    decide["decide.py<br/>the decision rule<br/>no AI"]
    summarize["summarize.py<br/>LLM CALL 2<br/>briefing, cases not approved"]
    story["story.py<br/>LLM CALL 3<br/>background of the note"]
    record["record.py<br/>append-only paper trail<br/>no AI"]
    app["Streamlit dashboard<br/>no AI at runtime"]
    np(["Nurse practitioner"])

    note --> extract --> decide
    wh --> lookup --> decide
    decide --> summarize --> record
    decide --> record
    note --> story --> app
    record --> app
    app <--> np
    np -. "appends a reviewer row" .-> record

    classDef ai fill:#e9d8fd,stroke:#6b46c1,color:#1a202c
    classDef code fill:#bee3f8,stroke:#2b6cb0,color:#1a202c
    classDef data fill:#e2e8f0,stroke:#4a5568,color:#1a202c
    class extract,summarize,story ai
    class lookup,decide,record,app code
    class note,wh data
```

Purple boxes are LLM calls. Blue boxes are ordinary code you can read and rerun. The three LLM calls are all the AI in the system:

| Call | Reads | Produces | Used for the decision? |
|---|---|---|---|
| `extract.py` | the clinical note | facts (diagnosis, age, HbA1c, metformin days), a quote for each, one confidence number | **Yes**: its facts are one of the two sources |
| `summarize.py` | the checks and the note | a short briefing for the reviewer | No: written after the decision |
| `story.py` | the note | a one-paragraph background of the patient | No: context only |

---

## 2. Warehouse vs AI review: two sources, one rule

Every policy criterion is checked **twice**: once in the warehouse by SQL, once in the note by the AI. Each source returns pass, fail, or unknown (it cannot say). The two are then combined:

| Warehouse | Note (AI) | Criterion result |
|---|---|---|
| pass | anything | **pass**: a warehouse pass is final |
| fail | fail | **fail** |
| fail | pass | **conflict** |
| fail | unknown | **fail** |
| unknown | pass or fail | whatever the note says |
| unknown | unknown | **unknown** |

---

## 3. The decision rule, conflicts, and the confidence threshold

```mermaid
flowchart TD
    start(["Each criterion checked<br/>against both sources"]) --> fail{"Any criterion<br/>FAILS?"}
    fail -- yes --> deny["DENY"]
    fail -- no --> conflict{"Any CONFLICT?<br/>warehouse and note disagree"}
    conflict -- yes --> review1["REVIEW<br/>reviewer sees both values"]
    conflict -- no --> unknown{"Any fact UNKNOWN<br/>in both sources?"}
    unknown -- yes --> review2["REVIEW"]
    unknown -- no --> tol{"A lab below its minimum<br/>but within tolerance?"}
    tol -- yes --> review3["REVIEW<br/>reviewer may approve"]
    tol -- no --> whpass{"Warehouse alone<br/>passes every criterion?"}
    whpass -- yes --> approve1["APPROVE"]
    approve1 --> flag{"AI confidence<br/>below 0.9?"}
    flag -- yes --> aiflag["Approved, with an<br/>AI FLAG to watch"]
    flag -- no --> clean["Approved"]
    whpass -- no --> conf{"AI confidence<br/>at least 0.9?"}
    conf -- yes --> approve2["APPROVE<br/>note was needed to pass"]
    conf -- no --> review4["REVIEW"]

    classDef bad fill:#fed7d7,stroke:#c53030,color:#1a202c
    classDef ok fill:#c6f6d5,stroke:#2f855a,color:#1a202c
    classDef rev fill:#fefcbf,stroke:#b7791f,color:#1a202c
    class deny bad
    class approve1,approve2,clean,aiflag ok
    class review1,review2,review3,review4 rev
```

---

## TODO: Feature: NP feedback as labels for ML

Use NP decisions to tune the system. ML never approves or denies.

1. **Collect labels.** For each problem criterion, the NP marks which source was right: warehouse, note, or neither. Also send a random 5% of auto-approvals to an NP.
2. **Check the AI.** Measure how often its reading is right. If it is reliable, lower the confidence gate.
3. **Set the tolerance.** See how often NPs approve near misses, and set the cost dial from that.
