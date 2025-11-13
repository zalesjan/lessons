# pages/1_Methods.py
import streamlit as st
import json
from supabase import create_client

def safe_json_load(x):
            if not x or x in ("", "null", "None"):
                return []
            if isinstance(x, (list, dict)):
                return x
            try:
                return json.loads(x)
            except Exception:
                return [str(x)]
            
st.set_page_config(page_title="Methods", page_icon="🧩", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "en"
lang = st.sidebar.selectbox("Language / Jazyk", ["en", "cs"], index=0 if st.session_state.lang=="en" else 1)
st.session_state.lang = lang

# --- Supabase client ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# --- Language ---
lang = st.session_state.get("lang", "en")
title = {
    "en": "Didactic methods",
    "cs": "Didaktické metody",
    "fr": "Méthodes didactiques",
    "es": "Métodos didácticos",
    "pt": "Métodos didáticos",
    "de": "Didaktische Methoden",
    "pl": "Metody dydaktyczne"
}.get(lang, "Didactic methods")

st.title(title)

# --- Load methods ---
@st.cache_data(ttl=300)
def load_methods():
    return supabase.table("methods").select("*").execute().data or []

methods = load_methods()

method_qs = st.query_params.get("method", None)

# --- Render ---
for m in methods:

    m_id = str(m.get("id"))
    opened = (m_id == method_qs)

    # Get translated fields with fallback
    name = m.get(f"name_{lang}") or m.get("name") or "Unnamed method"
    description = m.get(f"description{lang}") or m.get("description")

    before = safe_json_load(m["before"])
    after = safe_json_load(m["after"])

    steps = m.get(f"content_md_{lang}") or m.get("content_md")
    
    tips = m.get(f"tips_{lang}") or m.get("tips")

    with st.container(border=True):
        cols = st.columns([0.7, 0.3])
        with cols[0]:
            st.subheader(name)
            if description:
                st.write(description)
        with cols[1]:
            if st.button(("Hide manual" if opened else "▶ Watch manual"), key=f"btn-{m_id}"):
                if opened:
                    st.query_params.clear()
                else:
                    st.query_params["method"] = m_id
                st.rerun()
        with cols[1]:
            st.write("Tip - try this method before:")
            if before:
                for title, details in before.items():
                    # details is a list like ["Description", 5]
                    description = details[0] if len(details) > 0 else ""
                    duration = details[1] if len(details) > 1 else None
                    mins = f" — {duration} min" if duration else ""
                    st.markdown(f"- **{title}**{mins}  \n  {description}")

        with cols[1]:
            st.write("Tip - try this method after:")
            if after:
                for title, details in after.items():
                    # details is a list like ["Description", 5]
                    description = details[0] if len(details) > 0 else ""
                    duration = details[1] if len(details) > 1 else None
                    mins = f" — {duration} min" if duration else ""
                    st.markdown(f"- **{title}**{mins}  \n  {description}")

        meta = []
        if m.get("age_group"):
            vals = safe_json_load(m["age_group"])
            if vals:
                meta.append("**Use for:** " + ", ".join(map(str, vals)))

        if m.get("tags"):
                    meta.append(str(m["tags"]))

        if m.get("time"):
            meta.append("**Time:** " + str(m["time"]))

        if m.get("tools"):
            mats = safe_json_load(m["tools"])
            if mats:
                meta.append("**Materials:** " + ", ".join(map(str, mats)))

        if meta:
            st.write(" · ".join(meta))


        # Steps
        if steps:
            steps = json.loads(steps) if isinstance(steps, str) else steps
            st.markdown("**Suggested steps**")
            for title, details in steps.items():
                # details is a list like ["Description", 5]
                description = details[0] if len(details) > 0 else ""
                duration = details[1] if len(details) > 1 else None
                mins = f" — {duration} min" if duration else ""
                st.markdown(f"- **{title}**{mins}  \n  {description}")

        # Tips
        if tips:
            tips = json.loads(tips) if isinstance(tips, str) else tips
            st.markdown("**Tips**")
            for tip in tips:
                st.markdown(f"- {tip}")

        # Video
        if opened and m.get("videoUrl"):
            st.video(m["videoUrl"])
