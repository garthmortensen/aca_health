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
from datetime import datetime

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
OUTCOMES = ["All", "unclear", "deny", "approve", "request_more_info", "ai_flag"]
STATUS_LABEL = {"All": "All", "unclear": "Review", "deny": "Denied", "approve": "Approved",
                "request_more_info": "Awaiting info", "ai_flag": "AI flag"}
# Translucent tints, so the same colors read as pastel in light mode and muted in dark mode.
# The text keeps the theme's own color.
STATUS_COLOR = {"unclear": "rgba(217, 164, 6, 0.20)", "deny": "rgba(200, 70, 70, 0.20)",
                "approve": "rgba(60, 160, 90, 0.20)", "request_more_info": "rgba(70, 130, 200, 0.20)"}
CHECK_COLOR = {"Pass": "rgba(60, 160, 90, 0.20)", "Fail": "rgba(200, 70, 70, 0.20)",
               "Unknown": "rgba(128, 128, 128, 0.20)", "Conflict": "rgba(217, 164, 6, 0.20)",
               "Within tolerance": "rgba(70, 130, 200, 0.20)"}


SHORT = {c["id"]: c.get("short", c["question"]) for c in POLICY["criteria"]}


def basis(check: dict) -> str:
    """Which source(s) put a criterion where it is."""
    w, n = check["warehouse"]["status"], check["note"]["status"]
    if w == n:
        return "warehouse and note agree"
    return "warehouse only" if n == "unknown" else "AI reading of note only"


def criteria_met(checks) -> str:
    """'4 of 5': how many policy criteria pass. Conflicts and unknowns do not count as met."""
    if isinstance(checks, str):
        checks = json.loads(checks)
    return f"{sum(c.get('status') == 'pass' for c in checks)} of {len(checks)}" if checks else ""


def why(outcome: str, reason: str, checks_json: str | None) -> str:
    """One plain line for the queue: the criteria behind the outcome, and which source says so."""
    checks = json.loads(checks_json) if checks_json else []
    if not checks or not all("warehouse" in c for c in checks):
        return reason or ""  # written before the two-source checks, so show the stored reason
    named = lambda c: SHORT.get(c["id"], c["question"])  # noqa: E731
    fails = [f"{named(c)} ({basis(c)})" for c in checks if c["status"] == "fail"]
    if fails:
        return "Unmet: " + "; ".join(fails)
    conflicts = [named(c) for c in checks if c["status"] == "conflict"]
    if conflicts:
        return "Sources disagree on: " + "; ".join(conflicts)
    unknown = [named(c) for c in checks if c["status"] == "unknown"]
    if unknown:
        return "Not found for: " + "; ".join(unknown)
    near = [named(c) for c in checks if c["status"] == "near"]
    if near:
        return "Below the minimum, within tolerance: " + "; ".join(near)
    return reason or ""


def shade(color: str | None) -> str:
    return f"background-color: {color}" if color else ""
STARTERS = {
    "approve": ["All policy criteria are met.", "Conflict reviewed; the warehouse record is correct."],
    "deny": ["Does not meet the criterion: ", "Required documentation was not provided."],
    "request_more_info": ["Please submit a recent HbA1c result.", "Please document prior metformin use."],
}
CHECK_LABEL = {"pass": "Pass", "fail": "Fail", "near": "Within tolerance", "unknown": "Unknown", "conflict": "Conflict"}

QUEUE_SQL = """
with ai as (  -- the latest system row per request
    select prior_authorization_request_id,
           confidence,
           checks::varchar as checks,
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
       ai.checks,
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


@st.cache_data
def load_stories() -> dict:
    path = os.path.join(HERE, "data", "stories.jsonl")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {s["prior_authorization_request_id"]: s["story"] for s in map(json.loads, f)}


# --------------------------------------------------------------------- layout
st.set_page_config(page_title="Prior authorization review", layout="wide")
st.session_state.setdefault("status", "unclear")  # open on the cases that need a person
st.session_state.setdefault("queue_version", 0)


def set_status(status: str) -> None:
    st.session_state.status = status


with st.sidebar:
    reviewer = st.text_input("Your Name", value="Florence Nightingale")
    st.selectbox("Policy", ["GLP-1"])
    with st.expander("About this policy"):
        st.markdown(f"**{POLICY['name']}**  \nVersion {POLICY['version']}")
        st.markdown("**Criteria**")
        for c in POLICY["criteria"]:
            st.markdown(f"- {c['question']}")
        st.markdown(f"AI confidence floor: **{CONFIG['decision']['confidence_threshold']}**")
        st.caption("The system approves clear cases; everything else waits for a reviewer. "
                   "Every action is appended to the paper trail.")

outcome_filter = st.session_state.status  # set by the status tiles
everything = load_queue()
# AI flag: approved by the system, but the AI's reading of the note was weak or missing. The approval stands.
floor = CONFIG["decision"]["confidence_threshold"]
everything["ai_flag"] = ((everything.current_outcome == "approve") & (everything.last_decided_by == "system")
                         & (everything.ai_confidence.isna() | (everything.ai_confidence < floor)))
counts = everything.current_outcome.value_counts()
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
first_name = reviewer.split()[0] if reviewer.strip() else "there"
waiting = int(counts.get("unclear", 0))

st.title("Prior authorization review")
st.subheader(f"{greeting}, {first_name}. " + (
    f"{waiting} case{'s' if waiting != 1 else ''} need{'' if waiting != 1 else 's'} your review."
    if waiting else "Nothing is waiting for you right now."))
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

tiles = st.columns(len(OUTCOMES))
for col, key in zip(tiles, OUTCOMES):
    n = len(everything) if key == "All" else int(everything.ai_flag.sum()) if key == "ai_flag" else int(counts.get(key, 0))
    label = f"{'All cases' if key == 'All' else STATUS_LABEL[key]}  ·  {n}"
    col.button(label, key=f"tile_{key}", width="stretch", on_click=set_status, args=(key,),
               type="primary" if st.session_state.status == key else "secondary")

queue = everything.copy()
if outcome_filter == "ai_flag":
    queue = queue[queue.ai_flag]
elif outcome_filter != "All":
    queue = queue[queue.current_outcome == outcome_filter]

# Whole days since the request was made; the oldest case first
queue["case_age"] = (pd.Timestamp.today().normalize() - pd.to_datetime(queue.request_date)).dt.days
queue = queue.sort_values(["case_age", "request_id"], ascending=[False, True]).reset_index(drop=True)
queue["criteria_met"] = queue.checks.map(criteria_met)
queue["why"] = [why(o, r, c) for o, r, c in zip(queue.current_outcome, queue.reason, queue.checks)]

st.markdown(f"**{STATUS_LABEL[outcome_filter]}** ({len(queue)}), oldest first. Select a row to open the case.")
table = queue[["request_id", "drug_name", "criteria_met", "why", "case_age"]]
# The status is in the tiles above; each ID cell carries its status color, which matters when the filter is All
styled = table.style.apply(lambda col: [shade(STATUS_COLOR.get(o)) for o in queue.current_outcome], subset=["request_id"])
selection = st.dataframe(
    styled, hide_index=True, width="stretch",
    key=f"queue_{st.session_state.queue_version}_{outcome_filter}",
    on_select="rerun", selection_mode="single-row",
    column_config={"request_id": "ID",
                   "drug_name": "Drug",
                   "criteria_met": "Criteria met",
                   "why": st.column_config.TextColumn("Why", width="large"),
                   "case_age": st.column_config.NumberColumn("Case Age (days)", format="%d")},
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
st.markdown(f"Current status: **{STATUS_LABEL.get(case.current_outcome, case.current_outcome)}** (by {"Automated check" if case.last_decided_by == "system" else case.last_decided_by})")

story = load_stories().get(selected_id)
if story:
    st.markdown("**Case background**")
    st.caption("Written by AI from the clinical note, for context only. It does not check the policy or recommend anything.")
    st.write(story)


def shown(source: dict) -> str:
    """One source's answer for the table: the value, then the evidence behind it."""
    parts = [str(source["value"])] if source.get("value") is not None else []
    if source.get("evidence"):
        parts.append(source["evidence"])
    return "  ·  ".join(parts) or "—"


left, right = st.columns([3, 2], gap="large")

with left:
    if system_row is not None:
        st.markdown(f"**System assessment** — criteria met: **{criteria_met(system_row.checks)}**. "
                f"{system_row.reason}  (AI confidence {system_row.confidence})")
        if system_row.summary:
            st.info(f"**AI briefing** (information only, not a recommendation)\n\n{system_row.summary}")

        # Rows written before the two-source checks have no warehouse/note breakdown, so show those as they are
        checks = [c for c in (system_row.checks or []) if "warehouse" in c]
        for c in checks:
            if c["status"] == "conflict":
                st.warning(f"**Sources disagree — {c['question']}**\n\n"
                           f"Warehouse: {shown(c['warehouse'])}\n\nNote: {shown(c['note'])}")
        shortfalls = [c["shortfall"] for c in checks if c.get("shortfall")]
        if shortfalls:
            st.info("**Below the minimum, within tolerance**\n\n" + "\n\n".join(f"- {f}" for f in shortfalls))
        if checks:
            rows = pd.DataFrame([{
                "Status": CHECK_LABEL.get(c["status"], ""),
                "Criterion": c["question"],
                "Warehouse": shown(c["warehouse"]),
                "Clinical note (AI)": shown(c["note"]),
            } for c in checks])
            st.table(rows.style.map(lambda v: shade(CHECK_COLOR.get(v)), subset=["Status"]))
        elif system_row.checks:
            st.table(pd.DataFrame(system_row.checks).astype(str))

with right:
    st.markdown("**Clinical note**")
    with st.container(height=420, border=True):
        st.text(load_notes().get(selected_id, "(note not found)"))

    with st.expander("History", expanded=True):
        mine = (history.decided_by == reviewer).tolist()  # your own actions stand out
        st.dataframe(history[["decided_at", "decided_by", "outcome", "reason", "np_rationale", "policy_version"]].style.apply(
                         lambda row: ["background-color: #e8f4ea" if mine[row.name] else ""] * len(row), axis=1),
                     hide_index=True, width="stretch")

st.divider()
st.markdown("**Your decision**")


def add_starter() -> None:
    phrase = st.session_state.starter
    if phrase:
        st.session_state.rationale = (st.session_state.get("rationale", "") + " " + phrase).strip()
    st.session_state.starter = None


def record_decision() -> None:
    outcome, rationale = st.session_state.outcome, st.session_state.get("rationale", "").strip()
    if not rationale:
        st.session_state.rationale_error = True
        return
    write_np_decision(selected_id, outcome, rationale, reviewer, POLICY["id"], POLICY["version"])
    st.session_state.flash = (f"Thank you, {first_name}. {selected_id} is recorded as "
                              f"{outcome.replace('_', ' ')}. The next case is open below.")
    st.session_state.rationale = ""
    st.session_state.queue_version += 1  # clears the row selection, so the first case in the queue opens
    load_queue.clear()


outcome = st.radio("Outcome", ["approve", "deny", "request_more_info"], horizontal=True, key="outcome",
                   format_func=lambda o: o.replace("_", " "))
st.pills("Starter phrases (optional)", STARTERS[outcome], key="starter", on_change=add_starter)
st.text_area("Rationale (required; this goes in the record)", key="rationale")
if st.session_state.pop("rationale_error", False):
    st.error("A rationale is required.")
st.button("Record decision", type="primary", on_click=record_decision)
