"""Prior Auth Triage: the queue, and for the selected case only what needs attention. No decision here."""
from pbm.dashboard import common as c
import streamlit as st

reviewer = c.sidebar()
st.title("Prior authorization review")
st.caption("Prior Auth Triage · see which cases need attention and why. Open Member Story Review to decide.")
everything = c.load_queue()
c.greeting(everything, reviewer)
queue = c.tiles(everything)

table = queue[["request_id", "drug_name", "criteria_met", "why", "case_age"]]
selection = st.dataframe(
    table.style.apply(lambda col: [c.shade(c.STATUS_COLOR.get(o)) for o in queue.current_outcome], subset=["request_id"]),
    hide_index=True, width="stretch", height=min(38 + 35 * len(table), 250),
    key=f"t_queue_{st.session_state.get('queue_version', 0)}_{st.session_state.status}",
    on_select="rerun", selection_mode="single-row",
    column_config={"request_id": "ID", "drug_name": "Drug", "criteria_met": "Criteria met",
                   "why": st.column_config.TextColumn("Why", width="large"),
                   "case_age": st.column_config.NumberColumn("Case Age (days)", format="%d")})
rows = selection.selection.rows
if not len(table):
    st.info("No cases match.")
    st.stop()
selected = table.iloc[rows[0] if rows else 0].request_id
case = queue[queue.request_id == selected].iloc[0]
history = c.load_history(selected)
system, checks = c.case_checks(history)

st.divider()
st.subheader(f"{selected} · {case.drug_name}")
st.markdown(f"**{case.criteria_met}** criteria met · {c.STATUS_LABEL.get(case.current_outcome)} "
            f"(by {c.decided_by(case.last_decided_by)}) · {case.case_age} days old · {case.prescriber_specialty}")

# The problem: only the criteria that need attention
problems = [x for x in checks if x["status"] in c.PROBLEM]
if problems:
    for p in problems:
        c.problem_box(p)
elif system is not None:
    st.success(f"No open problems. {system.reason}")
