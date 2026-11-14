"""Shared pieces for the reviewer dashboard pages: data, labels, the status tiles and the decision form.

Recording a decision appends a row to the paper trail, review.prior_authorization_decision.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st
import yaml

PBM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PBM))  # repo root, for `import pbm`

from pbm.db import connect  # noqa: E402
from pbm.record import write_np_decision  # noqa: E402

CONFIG = yaml.safe_load(open(os.path.join(PBM, "config.yaml")))
POLICY = CONFIG["policy"]
FLOOR = CONFIG["decision"]["confidence_threshold"]
OUTCOMES = ["All", "unclear", "deny", "approve", "request_more_info", "ai_flag"]
STATUS_LABEL = {"All": "All cases", "unclear": "Review", "deny": "Denied", "approve": "Approved",
                "request_more_info": "Awaiting info", "ai_flag": "AI flag"}
# Translucent tints, so the same colors read as pastel in light mode and muted in dark mode
STATUS_COLOR = {"unclear": "rgba(217, 164, 6, 0.20)", "deny": "rgba(200, 70, 70, 0.20)",
                "approve": "rgba(60, 160, 90, 0.20)", "request_more_info": "rgba(70, 130, 200, 0.20)"}
CHECK_LABEL = {"pass": "Pass", "fail": "Fail", "near": "Within tolerance", "unknown": "Unknown", "conflict": "Conflict"}
CHECK_COLOR = {"Pass": "rgba(60, 160, 90, 0.20)", "Fail": "rgba(200, 70, 70, 0.20)",
               "Unknown": "rgba(128, 128, 128, 0.20)", "Conflict": "rgba(217, 164, 6, 0.20)",
               "Within tolerance": "rgba(70, 130, 200, 0.20)"}
PROBLEM = ("fail", "conflict", "unknown", "near")
SHORT = {c["id"]: c.get("short", c["question"]) for c in POLICY["criteria"]}
STARTERS = {
    "approve": ["All policy criteria are met.", "Conflict reviewed; the warehouse record is correct."],
    "deny": ["Does not meet the criterion: ", "Required documentation was not provided."],
    "request_more_info": ["Please submit a recent HbA1c result.", "Please document prior metformin use."],
}

QUEUE_SQL = """
with ai as (  -- the latest system row per request
    select prior_authorization_request_id, confidence, checks::varchar as checks
    from review.prior_authorization_decision
    where decided_by = 'system'
    qualify row_number() over (partition by prior_authorization_request_id order by decided_at desc, decision_id desc) = 1
)
select s.prior_authorization_request_id as request_id, s.current_outcome, s.last_decided_by, s.reason,
       ai.confidence as ai_confidence, ai.checks,
       r.member_id, r.drug_name, r.request_date, r.prescriber_specialty,
       (select m.first_name || ' ' || m.last_name from dw.dim_member m where m.member_id = r.member_id
        order by m.is_current desc limit 1) as member_name
from review.prior_authorization_status s
left join dw.fct_prior_authorization_request r using (prior_authorization_request_id)
left join ai using (prior_authorization_request_id)
"""

HISTORY_SQL = """
select decided_at, decided_by, outcome, reason, confidence, checks, summary, np_rationale, policy_version
from review.prior_authorization_decision
where prior_authorization_request_id = ?
order by decided_at, decision_id
"""


# ---------------------------------------------------------------------- data
@st.cache_data(ttl=5)
def load_queue() -> pd.DataFrame:
    with connect() as conn:
        q = conn.execute(QUEUE_SQL).df()
    q["ai_flag"] = ((q.current_outcome == "approve") & (q.last_decided_by == "system")
                    & (q.ai_confidence.isna() | (q.ai_confidence < FLOOR)))
    q["member_name"] = q.member_name.str.title()
    q["case_age"] = (pd.Timestamp.today().normalize() - pd.to_datetime(q.request_date)).dt.days
    q["criteria_met"] = q.checks.map(criteria_met)
    q["why"] = [why(r, c) for r, c in zip(q.reason, q.checks)]
    q["why_short"] = [why(r, c, short=True) for r, c in zip(q.reason, q.checks)]
    return q.sort_values(["case_age", "request_id"], ascending=[False, True]).reset_index(drop=True)


def load_history(request_id: str) -> pd.DataFrame:
    with connect() as conn:
        history = conn.execute(HISTORY_SQL, [request_id]).df()
    history["checks"] = history["checks"].map(lambda c: json.loads(c) if isinstance(c, str) else None)
    return history


@st.cache_data
def load_notes() -> dict:
    with open(os.path.join(PBM, "data", "notes.jsonl")) as f:
        return {n["prior_authorization_request_id"]: n["note"] for n in map(json.loads, f)}


@st.cache_data
def load_stories() -> dict:
    path = os.path.join(PBM, "data", "stories.jsonl")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {s["prior_authorization_request_id"]: s["story"] for s in map(json.loads, f)}


def case_checks(history: pd.DataFrame) -> tuple[pd.Series | None, list]:
    """The latest system row and its two-source checks."""
    system = history[history.decided_by == "system"]
    if system.empty:
        return None, []
    row = system.iloc[-1]
    return row, [c for c in (row.checks or []) if "warehouse" in c]


# -------------------------------------------------------------------- labels
def criteria_met(checks) -> str:
    """'4 of 5': criteria that pass. Conflicts, unknowns and near misses do not count as met."""
    if isinstance(checks, str):
        checks = json.loads(checks)
    return f"{sum(c.get('status') == 'pass' for c in checks)} of {len(checks)}" if checks else ""


def basis(check: dict) -> str:
    """Which source(s) put a criterion where it is."""
    w, n = check["warehouse"]["status"], check["note"]["status"]
    if w == n:
        return "warehouse and note agree"
    return "warehouse only" if n == "unknown" else "AI reading of note only"


def why(reason: str, checks_json: str | None, short: bool = False) -> str:
    """One plain line saying why a case is where it is. short=True drops the source."""
    checks = json.loads(checks_json) if checks_json else []
    if not checks or not all("warehouse" in c for c in checks):
        return reason or ""  # written before the two-source checks, so show the stored reason
    named = lambda c: SHORT.get(c["id"], c["question"])  # noqa: E731
    for status, lead in (("fail", "Unmet"), ("conflict", "Sources disagree"), ("unknown", "Not found"),
                         ("near", "Within tolerance")):
        hit = [c for c in checks if c["status"] == status]
        if hit:
            if short:
                return f"{lead}: " + "; ".join(named(c) for c in hit)
            items = [f"{named(c)} ({basis(c)})" if status == "fail" else named(c) for c in hit]
            return f"{lead}: " + "; ".join(items)
    return reason or ""


def shown(source: dict) -> str:
    """One source's answer: the value, then the evidence behind it."""
    parts = [str(source["value"])] if source.get("value") is not None else []
    if source.get("evidence"):
        parts.append(source["evidence"])
    return "  ·  ".join(parts) or "—"


def decided_by(name: str) -> str:
    return "Automated check" if name == "system" else name


def shade(color: str | None) -> str:
    return f"background-color: {color}" if color else ""


def criteria_table(checks: list) -> None:
    rows = pd.DataFrame([{"Status": CHECK_LABEL.get(c["status"], ""), "Criterion": c["question"],
                          "Warehouse": shown(c["warehouse"]), "Clinical note (AI)": shown(c["note"])} for c in checks])
    st.table(rows.style.map(lambda v: shade(CHECK_COLOR.get(v)), subset=["Status"]))


def problem_box(c: dict) -> None:
    """One criterion that needs attention, with both sources side by side."""
    label = CHECK_LABEL[c["status"]]
    body = (f"**{label}: {SHORT.get(c['id'], c['question'])}**\n\n"
            f"Warehouse: {shown(c['warehouse'])}\n\nNote: {shown(c['note'])}")
    if c.get("shortfall"):
        body += f"\n\n{c['shortfall']}"
    (st.error if c["status"] == "fail" else st.warning)(body)


def note_with_quote(note: str, quote: str | None) -> str:
    """The note as HTML, with the quote highlighted when it is found verbatim."""
    text = html.escape(note)
    if quote and html.escape(quote) in text:
        text = text.replace(html.escape(quote), f"<mark>{html.escape(quote)}</mark>", 1)
    return f"<div style='white-space: pre-wrap; font-family: monospace; font-size: 0.85em'>{text}</div>"


def history_table(history: pd.DataFrame, reviewer: str) -> None:
    """The request's decisions in order, with the reviewer's own rows shaded."""
    mine = (history.decided_by == reviewer).tolist()
    view = history[["decided_at", "decided_by", "outcome", "reason", "np_rationale"]].copy()
    view["decided_by"] = view.decided_by.map(decided_by)
    st.dataframe(view.style.apply(lambda r: ["background-color: rgba(60, 160, 90, 0.20)" if mine[r.name] else ""] * len(r), axis=1),
                 hide_index=True, width="stretch")


# ---------------------------------------------------------------------- page
def sidebar() -> str:
    with st.sidebar:
        reviewer = st.text_input("Your Name", value="Florence Nightingale", key="reviewer")
        st.selectbox("Policy", ["GLP-1"], key="policy")
        with st.expander("About this policy"):
            st.markdown(f"**{POLICY['name']}**  \nVersion {POLICY['version']}")
            for c in POLICY["criteria"]:
                st.markdown(f"- {c['question']}")
            st.markdown(f"AI confidence floor: **{FLOOR}**")
    return reviewer


def greeting(everything: pd.DataFrame, reviewer: str) -> None:
    hour = datetime.now().hour
    hello = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    name = reviewer.split()[0] if reviewer.strip() else "there"
    n = int((everything.current_outcome == "unclear").sum())
    st.subheader(f"{hello}, {name}. " + (f"{n} case{'s' if n != 1 else ''} need{'' if n != 1 else 's'} your review."
                                         if n else "Nothing is waiting for you right now."))
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))


def _set_status(status: str) -> None:
    st.session_state.status = status


def tiles(everything: pd.DataFrame) -> pd.DataFrame:
    """Status buttons that filter the queue. Returns the filtered queue."""
    st.session_state.setdefault("status", "unclear")  # open on the cases that need a person
    counts = everything.current_outcome.value_counts()
    for col, key in zip(st.columns(len(OUTCOMES)), OUTCOMES):
        n = len(everything) if key == "All" else int(everything.ai_flag.sum()) if key == "ai_flag" else int(counts.get(key, 0))
        col.button(f"{STATUS_LABEL[key]} · {n}", key=f"tile_{key}", width="stretch",
                   on_click=_set_status, args=(key,), type="primary" if st.session_state.status == key else "secondary")
    status = st.session_state.status
    if status == "ai_flag":
        return everything[everything.ai_flag].reset_index(drop=True)
    if status != "All":
        return everything[everything.current_outcome == status].reset_index(drop=True)
    return everything


def _add_starter(prefix: str) -> None:
    phrase = st.session_state[f"{prefix}_starter"]
    if phrase:
        st.session_state[f"{prefix}_rationale"] = (st.session_state.get(f"{prefix}_rationale", "") + " " + phrase).strip()
    st.session_state[f"{prefix}_starter"] = None


def _record(prefix: str, request_id: str, reviewer: str) -> None:
    outcome = st.session_state[f"{prefix}_outcome"]
    rationale = st.session_state.get(f"{prefix}_rationale", "").strip()
    if not outcome or not rationale:
        st.session_state[f"{prefix}_error"] = "Choose an outcome and write a rationale."
        return
    write_np_decision(request_id, outcome, rationale, reviewer, POLICY["id"], POLICY["version"])
    name = reviewer.split()[0] if reviewer.strip() else "there"
    st.session_state.flash = f"Thank you, {name}. {request_id} is recorded as {outcome.replace('_', ' ')}. The next case is open."
    st.session_state[f"{prefix}_rationale"] = ""
    st.session_state.queue_version = st.session_state.get("queue_version", 0) + 1
    load_queue.clear()


def decision_form(prefix: str, request_id: str, reviewer: str) -> None:
    """Outcome, optional starter phrases, rationale, and Record."""
    options = ["approve", "deny", "request_more_info"]
    outcome = st.radio("Outcome", options, horizontal=True, key=f"{prefix}_outcome",
                       format_func=lambda o: o.replace("_", " ").capitalize())
    st.pills("Starter phrases (optional)", STARTERS[outcome], key=f"{prefix}_starter",
             on_change=_add_starter, args=(prefix,))
    st.text_area("Rationale (required; this goes in the record)", key=f"{prefix}_rationale", height=90)
    if err := st.session_state.pop(f"{prefix}_error", None):
        st.error(err)
    st.button("Record decision", type="primary", key=f"{prefix}_record", on_click=_record, args=(prefix, request_id, reviewer))
