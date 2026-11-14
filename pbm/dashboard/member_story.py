"""Member Story Review: what needs attention, the patient's story, each criterion with the note beside it, then the decision."""
from pbm.dashboard import common as c
import streamlit as st

reviewer = c.sidebar()
st.title("Prior authorization review")
st.caption("Member Story Review: see what needs attention, read the patient's story, walk through each criterion with the note beside it, then decide.")
everything = c.load_queue()
c.greeting(everything, reviewer)
queue = c.tiles(everything)
if queue.empty:
    st.info("No cases match.")
    st.stop()

# A compact picker instead of a table: the case is the page
labels = {r.request_id: f"{r.request_id} · {r.drug_name} · {r.criteria_met} met · {r.why_short}" for r in queue.itertuples()}
selected = st.selectbox("Case", list(labels), format_func=labels.get,
                        key=f"s_case_{st.session_state.get('queue_version', 0)}_{st.session_state.status}")
case = queue[queue.request_id == selected].iloc[0]
history = c.load_history(selected)
system, checks = c.case_checks(history)

# Restart the walk-through when the case changes
if st.session_state.get("s_case_open") != selected:
    st.session_state.s_case_open, st.session_state.s_step = selected, 0

st.divider()
st.subheader(f"{selected} · {case.drug_name}")
st.markdown(f"{case.prescriber_specialty} · requested {case.request_date} · {case.case_age} days old · "
            f"{c.STATUS_LABEL.get(case.current_outcome)} (by {c.decided_by(case.last_decided_by)})")

# Case triage: what needs attention, before the story
problems = [x for x in checks if x["status"] in c.PROBLEM]
with st.container(border=True):
    st.markdown(f"**Case Triage** · {case.criteria_met} criteria met")
    if problems:
        for p in problems:
            c.problem_box(p)
    elif system is not None:
        st.success(f"No open problems. {system.reason}")

story = c.load_stories().get(selected)
with st.container(border=True):
    st.markdown(f"**{case.get('member_name') or case.member_id}**")
    st.write(story or "(no background written for this case)")
    st.caption("Written by AI from the clinical note, for context only.")

if system is not None and system.summary:
    st.info(f"**AI briefing**\n\n{system.summary}")

if not checks:
    st.info("This case was decided before the two-source checks, so there is nothing to step through.")
    st.stop()

def badge(status: str) -> str:
    """A small colored label for one verdict: PASS, FAIL, CONFLICT, ..."""
    label = c.CHECK_LABEL.get(status, status)
    return (f"<span style='{c.shade(c.CHECK_COLOR.get(label))}; padding: 2px 8px; border-radius: 4px; "
            f"font-weight: 600; font-size: 0.85em'>{label.upper()}</span>")


steps = len(checks)
step = st.session_state.s_step
current = checks[step]

left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown(f"**Criteria {step + 1}/{steps}**")
    for i, x in enumerate(checks):
        name = f"{i + 1}. {c.SHORT.get(x['id'], x['question'])}"
        if i == step:
            name = f"<b>▶ {name}</b>"
        style = "opacity: 0.55" if i > step else ""  # steps not reached yet are dimmed
        st.markdown(f"<div style='{style}'>{name} &nbsp;{badge(x['status'])}</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**{current['question']}**")
        # One small section per source: its verdict, its value, and the evidence behind it
        sources = {"warehouse": "Warehouse", "note": "Clinical note (AI)"}
        for col, (key, title) in zip(st.columns(2), sources.items()):
            src = current[key]
            with col.container(border=True):
                st.markdown(f"{title}  \n{badge(src.get('status', 'unknown'))}", unsafe_allow_html=True)
                st.markdown(f"### {src['value'] if src.get('value') is not None else '—'}")
                st.caption(src.get("evidence") or "Nothing found")
        # How the two verdicts combine into the criterion's result
        w, n = current["warehouse"].get("status", "unknown"), current["note"].get("status", "unknown")
        st.markdown(f"Warehouse {badge(w)} &nbsp;+&nbsp; Note {badge(n)} &nbsp;=&nbsp; {badge(current['status'])}",
                    unsafe_allow_html=True)
        if current.get("shortfall"):
            st.caption(current["shortfall"])
    back, nxt = st.columns(2)
    if back.button("◀ Back", disabled=step == 0, width="stretch"):
        st.session_state.s_step -= 1
        st.rerun()
    if nxt.button("Next ▶", disabled=step == steps - 1, type="primary", width="stretch"):
        st.session_state.s_step += 1
        st.rerun()

with right:
    st.markdown("**Clinical note** · the quote for this criterion is highlighted")
    with st.container(height=460, border=True):
        st.markdown(c.note_with_quote(c.load_notes().get(selected, "(note not found)"), current["note"].get("evidence")),
                    unsafe_allow_html=True)

st.divider()
if step == steps - 1:  # the decision opens on the last criterion
    with st.container(border=True):
        st.markdown("**Your decision**")
        c.decision_form("s", selected, reviewer)
    with st.expander("History"):
        c.history_table(history, reviewer)
else:
    st.caption(f"Step through all {steps} criteria to open the decision.")
