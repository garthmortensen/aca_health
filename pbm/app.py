"""Step 5: the reviewer's dashboard.

Left: the queue of prior authorization requests, filtered by current outcome and
sorted by AI confidence. Right: one case - the note, each policy criterion with
its quote, the AI's reason, the request's full history, and the reviewer's
action, which appends a row to review.prior_authorization_decision.

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

from pbm.record import connect, write_np_decision  # noqa: E402
CONFIG = yaml.safe_load(open(os.path.join(HERE, "config.yaml")))
POLICY = CONFIG["policy"]
OUTCOMES = ["All", "unclear", "deny", "approve", "request_more_info"]
STATUS_ICON = {"pass": "✅", "fail": "❌", "unknown": "❓"}

QUEUE_SQL = """
select s.prior_authorization_request_id as request_id,
       s.current_outcome,
       s.last_decided_by,
       s.last_decided_at,
       s.reason,
       ai.confidence as ai_confidence,
       r.member_id, r.drug_name, r.request_date, r.prescriber_specialty
from review.prior_authorization_status s
left join dw.fct_prior_authorization_request r using (prior_authorization_request_id)
left join lateral (
    select confidence from review.prior_authorization_decision d
    where d.prior_authorization_request_id = s.prior_authorization_request_id and d.decided_by = 'system'
    order by d.decided_at desc limit 1
) ai on true
order by ai.confidence desc nulls last, s.prior_authorization_request_id
"""

HISTORY_SQL = """
select decision_id, decided_at, decided_by, outcome, reason, confidence, checks, np_rationale, policy_version
from review.prior_authorization_decision
where prior_authorization_request_id = %s
order by decided_at, decision_id
"""


@st.cache_data(ttl=5)
def load_queue() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql(QUEUE_SQL, conn)


def load_history(request_id: str) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql(HISTORY_SQL, conn, params=(request_id,))


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
table = queue[["request_id", "current_outcome", "ai_confidence", "drug_name", "request_date", "last_decided_by"]]
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

if system_row is not None:
    st.markdown(f"**AI assessment** — {system_row.reason}  (confidence {system_row.confidence})")
    checks = system_row.checks or []
    st.table(pd.DataFrame([{
        "": STATUS_ICON.get(c["status"], ""),
        "Criterion": c["question"],
        "Value": "" if c["value"] is None else str(c["value"]),
        "Quote from note": c["quote"] or "— not documented —",
    } for c in checks]))

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
