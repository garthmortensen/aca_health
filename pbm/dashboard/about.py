"""About: renders pbm/About.md, with its Mermaid diagrams drawn by Mermaid in the browser."""
import json
import os
import re

import streamlit as st

ABOUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "About.md")
# Streamlit's markdown does not draw Mermaid, so each diagram goes into a small HTML frame.
# The HTML is built only from About.md in this repo, never from user or model input.
MERMAID_HTML = """
<div class="mermaid" id="d"></div>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  document.getElementById("d").textContent = {code};
  mermaid.initialize({{ startOnLoad: false, theme: "neutral" }});
  await mermaid.run({{ nodes: [document.getElementById("d")] }});
</script>
"""

text = open(ABOUT).read()
# Alternate markdown and diagram chunks; a diagram's height is a rough guess from its number of lines
for i, chunk in enumerate(re.split(r"```mermaid\n(.*?)```", text, flags=re.S)):
    if i % 2:
        lines = chunk.count("\n")
        height = 1000 if "flowchart TD" in chunk else max(300, 18 * lines)
        st.iframe(MERMAID_HTML.format(code=json.dumps(chunk)), height=height)
    elif chunk.strip():
        st.markdown(chunk)
