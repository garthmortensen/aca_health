"""Step 5: the reviewer's dashboard. Three pages:

  Prior Auth Triage     the queue, and for the selected case what needs attention and why
  Member Story Review   the case triage, the patient's story, the AI briefing, each criterion
                        step by step with the note beside it, then the reviewer's decision,
                        which appends a row to review.prior_authorization_decision
  About                 pbm/About.md, with its diagrams

The pages live in pbm/dashboard/.

Run from the repo root:
  streamlit run pbm/app.py
"""
import os
import sys

import streamlit as st

# Streamlit adds pbm/ to the import path, not the repo root, so add the root for `import pbm`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Prior authorization review", layout="wide")
page = st.navigation([
    st.Page("dashboard/triage.py", title="Prior Auth Triage", default=True),
    st.Page("dashboard/member_story.py", title="Member Story Review"),
    st.Page("dashboard/about.py", title="About"),
])

# Top bar on every page: links to the code and the warehouse's data dictionary
_, repo, docs = st.columns([6, 1, 1])
repo.link_button("GitHub repo", "https://github.com/garthmortensen/aca_health", width="stretch")
docs.link_button("Data dictionary", "https://garthmortensen.github.io/aca_health/", width="stretch")
page.run()
