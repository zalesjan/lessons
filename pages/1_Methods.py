# pages/1_Methods.py
import streamlit as st
from utils.data import methods

st.set_page_config(page_title="Methods", page_icon="🧩", layout="centered")

# --- CSS to make "cards" prettier ---
st.markdown("""
<style>
.method-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.method-card h3 {
    margin-top: 0;
    color: #1e40af;
}
</style>
""", unsafe_allow_html=True)

# --- Language toggle (reuse from session) ---
lang = st.session_state.get("lang", "en")
title = "Didactic methods" if lang == "en" else "Didaktické metody"

st.title(title)
st.caption("✨ Explore different teaching methods with details, tips, and example videos.")

# --- Tabs for each method ---
tabs = st.tabs([m.name for m in methods])

for m, tab in zip(methods, tabs):
    with tab:
        st.markdown(f"<div class='method-card'>", unsafe_allow_html=True)
        st.subheader(m.name)
        if m.summary:
            st.write(m.summary)

        # Meta info inline
        meta = []
        if m.useFor:   meta.append("**Use for:** " + ", ".join(m.useFor))
        if m.time:     meta.append("**Time:** " + m.time)
        if m.materials:meta.append("**Materials:** " + ", ".join(m.materials))
        if meta:
            st.markdown(" · ".join(meta))

        # Expanders for details
        if m.steps:
            with st.expander("📋 Suggested steps", expanded=False):
                for s in m.steps:
                    mins = f" — {s.durationMin} min" if s.durationMin else ""
                    st.markdown(f"- **{s.title}**{mins}  \n  {s.description}")

        if m.tips:
            with st.expander("💡 Tips", expanded=False):
                for tip in m.tips:
                    st.markdown(f"- {tip}")

        if m.videoUrl:
            with st.expander("🎥 Watch manual", expanded=False):
                st.video(m.videoUrl)

        st.markdown("</div>", unsafe_allow_html=True)
