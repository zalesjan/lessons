# pages/1_Methods.py
import streamlit as st
from utils.data import methods

st.set_page_config(page_title="Methods", page_icon="🧩", layout="centered")

# language (from session)
lang = st.session_state.get("lang", "en")
title = "Didactic methods" if lang == "en" else "Didaktické metody"

# which method to open (query param ?method=...)
method_qs = st.query_params.get("method", None)

st.title(title)

for m in methods:
    # auto-open if query param matches
    opened = (m.id == method_qs)

    with st.container(border=True):
        # Header row with a manual open/close button that also updates the URL
        cols = st.columns([0.7, 0.3])
        with cols[0]:
            st.subheader(m.name)
            if m.summary:
                st.write(m.summary)
        with cols[1]:
            if st.button(("Hide manual" if opened else "▶ Watch manual"), key=f"btn-{m.id}"):
                if opened:
                    # close: clear query param
                    st.query_params.clear()
                else:
                    # open: set method=<id>
                    st.query_params["method"] = m.id
                st.rerun()

        # Details
        meta = []
        if m.useFor:   meta.append("**Use for:** " + ", ".join(m.useFor))
        if m.time:     meta.append("**Time:** " + m.time)
        if m.materials:meta.append("**Materials:** " + ", ".join(m.materials))
        if meta:
            st.write(" · ".join(meta))

        # Steps
        if m.steps:
            st.markdown("**Suggested steps**")
            for s in m.steps:
                mins = f" — {s.durationMin} min" if s.durationMin else ""
                st.markdown(f"- **{s.title}**{mins}  \n  {s.description}")

        # Tips
        if m.tips:
            st.markdown("**Tips**")
            for tip in m.tips:
                st.markdown(f"- {tip}")

        # Video preview (shown when opened)
        if opened and m.videoUrl:
            st.video(m.videoUrl)
