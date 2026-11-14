"""Step 5: the reviewer's dashboard.

Left: the queue of prior authorization requests, filtered by current outcome and
sorted by AI confidence. Below it: one case - the AI briefing, each policy
criterion with what the warehouse shows next to what the note says (conflicts
highlighted), the note, the request's full history, and the reviewer's action,
which appends a row to review.prior_authorization_decision.

Run:
  streamlit run pbm/app.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd
import streamlit as st
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
# Streamlit adds pbm/ to the import path, not the repo root, so add the root for `import pbm`
sys.path.insert(0, os.path.dirname(HERE))

from pbm.db import connect  # noqa: E402
from pbm.record import write_np_decision  # noqa: E402
CONFIG = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))
POLICY = CONFIG["policy"]
OUTCOMES = ["All", "unclear", "deny", "approve", "request_more_info"]
STATUS_ICON = {"pass": "✅", "fail": "❌", "unknown": "❓", "conflict": "⚠️"}

QUEUE_SQL = """
with ai as (  -- the latest system row per request
    select prior_authorization_request_id,
           confidence,
           len(list_filter(json_extract_string(checks, '$[*].status'), lambda x: x = 'conflict')) as conflicts
    from review.prior_authorization_decision
    where decided_by = 'system'
    qualify row_number() over (partition by prior_authorization_request_id order by decided_at desc, decision_id desc) = 1
)
select s.prior_authorization_request_id as request_id,
       s.current_outcome,
       s.last_decided_by,
       s.last_decided_at,
       s.reason,
       ai.confidence as ai_confidence,
       ai.conflicts,
       r.member_id, r.drug_name, r.request_date, r.prescriber_specialty
from review.prior_authorization_status s
left join dw.fct_prior_authorization_request r using (prior_authorization_request_id)
left join ai using (prior_authorization_request_id)
order by ai.confidence desc nulls last, s.prior_authorization_request_id
"""

HISTORY_SQL = """
select decision_id, decided_at, decided_by, outcome, reason, confidence, checks, summary, np_rationale, policy_version
from review.prior_authorization_decision
where prior_authorization_request_id = ?
order by decided_at, decision_id
"""


@st.cache_data(ttl=5)
def load_queue() -> pd.DataFrame:
    with connect() as conn:
        return conn.execute(QUEUE_SQL).df()


def load_history(request_id: str) -> pd.DataFrame:
    with connect() as conn:
        history = conn.execute(HISTORY_SQL, [request_id]).df()
    # DuckDB returns JSON columns as text
    history["checks"] = history["checks"].map(lambda c: json.loads(c) if isinstance(c, str) else None)
    return history


@st.cache_data
def load_notes() -> dict:
    with open(os.path.join(HERE, "data", "notes.jsonl")) as f:
        return {n["prior_authorization_request_id"]: n["note"] for n in map(json.loads, f)}


# --------------------------------------------------------------------- layout
st.set_page_config(page_title="Prior authorization review", layout="wide")
st.title("Prior authorization review")
st.caption(f"Policy: {POLICY['name']} (version {POLICY['version']}). "
           "The system approves clear cases; everything else waits for a reviewer. Every action is appended to the paper trail.")

with st.sidebar:
    reviewer = st.text_input("Your name (recorded on each decision)", value="NP on duty")
    outcome_filter = st.selectbox("Show cases whose current outcome is", OUTCOMES)
    st.markdown("---")
    st.markdown("**Criteria**")
    for c in POLICY["criteria"]:
        st.markdown(f"- {c['question']}")
    st.markdown(f"\nAI confidence floor: **{CONFIG['decision']['confidence_threshold']}**")

queue = load_queue()
if outcome_filter != "All":
    queue = queue[queue.current_outcome == outcome_filter]


st.subheader(f"Queue ({len(queue)})")
counts = load_queue().current_outcome.value_counts()
st.caption("  ·  ".join(f"{k}: {v}" for k, v in counts.items()))
table = queue[["request_id", "current_outcome", "conflicts", "ai_confidence", "drug_name", "request_date", "last_decided_by"]]
selection = st.dataframe(
    table, hide_index=True, width="stretch",
    on_select="rerun", selection_mode="single-row",
    column_config={"ai_confidence": st.column_config.NumberColumn("AI confidence", format="%.2f")},
)
rows = selection.selection.rows if selection and selection.selection else []
selected_id = table.iloc[rows[0]]["request_id"] if rows else (table.iloc[0]["request_id"] if len(table) else None)

st.divider()
if selected_id is None:
    st.info("No cases match the filter.")
    st.stop()

case = queue[queue.request_id == selected_id].iloc[0]
history = load_history(selected_id)
system_row = history[history.decided_by == "system"].iloc[-1] if (history.decided_by == "system").any() else None

st.subheader(f"{selected_id}  —  {case.drug_name}")
st.markdown(f"Member **{case.member_id}** · requested {case.request_date} · prescriber {case.prescriber_specialty}")
st.markdown(f"Current outcome: **{case.current_outcome}** (by {case.last_decided_by})")

def shown(source: dict) -> str:
    """One source's answer for the table: the value, then the evidence behind it."""
    parts = [str(source["value"])] if source.get("value") is not None else []
    if source.get("evidence"):
        parts.append(source["evidence"])
    return "  ·  ".join(parts) or "—"


if system_row is not None:
    st.markdown(f"**System assessment** — {system_row.reason}  (AI confidence {system_row.confidence})")
    if system_row.summary:
        st.info(f"**AI briefing** (information only, not a recommendation)\n\n{system_row.summary}")

    # Rows written before the two-source checks have no warehouse/note breakdown, so show those as they are
    checks = [c for c in (system_row.checks or []) if "warehouse" in c]
    for c in checks:
        if c["status"] == "conflict":
            st.warning(f"**Sources disagree — {c['question']}**\n\n"
                       f"Warehouse: {shown(c['warehouse'])}\n\nNote: {shown(c['note'])}")
    if checks:
        rows = pd.DataFrame([{
            "": STATUS_ICON.get(c["status"], ""),
            "Criterion": c["question"],
            "Warehouse": shown(c["warehouse"]),
            "Clinical note (AI)": shown(c["note"]),
        } for c in checks])
        conflict = [c["status"] == "conflict" for c in checks]
        st.table(rows.style.apply(
            lambda row: ["background-color: #fff3cd" if conflict[row.name] else ""] * len(row), axis=1))
        fyis = [c["fyi"] for c in checks if c.get("fyi")]
        if fyis:
            st.info("**FYI: lab values close to their threshold**\n\n" + "\n\n".join(f"- {f}" for f in fyis))
    elif system_row.checks:
        st.table(pd.DataFrame(system_row.checks).astype(str))

with st.expander("Clinical note", expanded=case.current_outcome != "approve"):
    st.text(load_notes().get(selected_id, "(note not found)"))

with st.expander("History", expanded=True):
    st.dataframe(history[["decided_at", "decided_by", "outcome", "reason", "np_rationale", "policy_version"]],
                 hide_index=True, width="stretch")

st.markdown("**Your decision**")
with st.form("decision", clear_on_submit=True):
    outcome = st.radio("Outcome", ["approve", "deny", "request_more_info"], horizontal=True,
                       format_func=lambda o: o.replace("_", " "))
    rationale = st.text_area("Rationale (required; this goes in the record)")
    submitted = st.form_submit_button("Record decision")
if submitted:
    if not rationale.strip():
        st.error("A rationale is required.")
    else:
        write_np_decision(selected_id, outcome, rationale.strip(), reviewer, POLICY["id"], POLICY["version"])
        st.success(f"Recorded {outcome.replace('_', ' ')} by {reviewer}.")
        load_queue.clear()
        st.rerun()
