# pages/1_Methods.py
import streamlit as st
import json
import os
from datetime import date
from supabase import create_client, Client
from openai import OpenAI

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

t = {
    "en": {
        "title": "Composed Lesson Variants",
        "subtitle": "Each variant centers a different method and includes 1–2 lead-in and 1–2 consolidation steps.",
        "before": "**People tried this method before:**",
        "main_method": "Suggested steps",
        "after": "Try to go for this after",
        "subject": "Subject",
        "level": "Use for",
        "materials": "Be ready with",
        "open_method": "Open video",
    },
    "cs": {
        "title": "Kombinuj moderní didaktické metody a vytvoř super hodinu",
        "subtitle": "Každá varianta staví na jiné  hlavní metodě, a taky obsahuje 1–2 úvodní a 1–2 závěrečné aktivity.",
        "before": "Toto můžeš zařadit před:",
        "main_method": "Provedení metody / Doporučený postup",
        "after": "Toto můžeš zařadit po:",
        "subject": "Předmět",
        "level": "Určeno pro",
        "materials": "Připrav si",
        "open_method": "Otevřít video",
    },
}[lang]


st.title(title)
st.title(t["title"])
st.caption(t["subtitle"])
# --- Load methods ---
@st.cache_data(ttl=300)
def load_methods():
    return supabase.table("methods").select("*").execute().data or []

methods = load_methods()

def method_lang(id_value):
    """Extracts the language code after the second hyphen."""
    if not id_value or '-' not in id_value:
        return 'en'
    parts = id_value.split('-')
    return parts[-1] if len(parts[-1]) == 2 else 'en'

filtered_methods = [m for m in methods if method_lang(m.get("id", "")) == lang]

method_qs = st.query_params.get("method", None)

# --- Render ---
for m in filtered_methods:

    m_id = str(m.get("id"))
    opened = (m_id == method_qs)

    # Get translated fields with fallback
    name = m.get(f"name_{lang}") or m.get("name") or "Unnamed method"
    description = m.get(f"description{lang}") or m.get("description")

    before = safe_json_load(m["before"])
    after = safe_json_load(m["after"])
    content = safe_json_load(m["content_md"])
    
    tips = m.get(f"tips_{lang}") or m.get("tips")

    with st.container(border=True):
        cols = st.columns([0.7, 0.3])
        with cols[0]:
            st.subheader(name)
            if description:
                st.write(description)
        with cols[1]:
            if st.button("Hide manual" if opened else f"▶ {t['open_method']}: {name}", key=f"btn-{m_id}"):
                #("Hide manual" if opened else "▶ Watch manual"), key=f"btn-{m_id}"):
                if opened:
                    st.query_params.clear()
                else:
                    st.query_params["method"] = m_id
                st.rerun()

        with cols[1]:
            if before:
                st.markdown(f"##### {t['before']}")
                for step in sorted(before, key=lambda x: x.get("order", 0)):
                    title = step.get("title", "")
                    activity = step.get("activity", "")
                    minutes = step.get("minutes")
                    mins = f" — {minutes} min" if minutes else ""
                    st.markdown(f"- **{title}**{mins}  \n  {activity}")

        with cols[1]:
            if after:
                st.markdown(f"##### {t['after']}")
                for step in sorted(after, key=lambda x: x.get("order", 0)):
                    title = step.get("title", "")
                    activity = step.get("activity", "")
                    minutes = step.get("minutes")
                    mins = f" — {minutes} min" if minutes else ""
                    st.markdown(f"- **{title}**{mins}  \n  {activity}")

        meta = []
        if m.get("age_group"):
            vals = safe_json_load(m["age_group"])
            if vals:
                meta.append(f"**{t['level']}:** " + ", ".join(map(str, vals)))

        if m.get("tags"):
                    meta.append(str(m["tags"]))

        if m.get("time"):
            meta.append("**Time:** " + str(m["time"]))

        if m.get("tools"):
            mats = safe_json_load(m["tools"])
            if mats:
                meta.append(f"**{t['materials']}:** " + ", ".join(map(str, mats)))

        if meta:
            st.write(" · ".join(meta))


        # Steps
        if content:
            st.markdown(f"##### {t['main_method']}")
            for step in sorted(content, key=lambda x: x.get("order", 0)):
                title = step.get("title", "")
                activity = step.get("activity", "")
                minutes = step.get("minutes")
                mins = f" — {minutes} min" if minutes else ""
                st.markdown(f"- **{title}**{mins}  \n  {activity}")

        # Tips
        if tips:
            tips = json.loads(tips) if isinstance(tips, str) else tips
            st.markdown("**Tips**")
            for tip in tips:
                st.markdown(f"- {tip}")

        # Video
        if opened and m.get("videoUrl"):
            st.video(m["videoUrl"])



# Try Streamlit Cloud secrets first, then fall back to local env
api_key = st.secrets["open_AI"]["OPENAI_API_KEY"] or os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("❌ No OpenAI API key found. Please set it in Streamlit Secrets or as an environment variable.")
else:
    client = OpenAI(api_key=api_key)
MODEL = "gpt-4o-mini"

# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    # create profile if not exists
    supabase.table("profiles").insert({"id": user_id}).execute()
    return {"paid": False, "free_generations_used": 0, "last_generation_date": None}

def update_profile(user_id, data: dict):
    supabase.table("profiles").update(data).eq("id", user_id).execute()

# --------------------------------------------------
# Authentication UI
# --------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🎓 AI Lesson Generator")
    mode = st.radio("Select to:", ["Login", "Sign up"], horizontal=True)
    email = st.text_input("Email address")
    pw = st.text_input("Password", type="password")

    if mode == "Sign up":
        if st.button("Create Account"):
            try:
                auth_res = supabase.auth.sign_up({"email": email, "password": pw})
                if auth_res.user:
                    st.success("✅ Check your email to confirm registration.")
                else:
                    st.error("Could not sign up.")
            except Exception as e:
                st.error(str(e))
    else:  # Login
        if st.button("Login"):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                if auth_res.user:
                    st.session_state.user = auth_res.user
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            except Exception as e:
                st.error(str(e))
    st.stop()

# --------------------------------------------------
# Logged-in area
# --------------------------------------------------
user = st.session_state.user
profile = get_profile(user.id)
st.success(f"Welcome {user.email}!")

st.sidebar.button("Logout", on_click=lambda: st.session_state.pop("user"))

paid = profile.get("paid", False)
used = profile.get("free_generations_used", 0)
last = profile.get("last_generation_date")

today = str(date.today())
can_generate = False

if paid:
    st.info("💎 Premium access: unlimited generations.")
    can_generate = True
else:
    remaining = 7 - used
    st.warning(f"🆓 Free tier: {remaining} generations left (1 per day).")
    if used >= 7:
        st.error("No more free generations available.")
    elif last == today:
        st.error("Already generated today.")
    else:
        can_generate = True

# Manual “Pay” unlock
#if not paid and st.button("💳 Mark as Paid (Manual)"):
#    update_profile(user.id, {"paid": True})
#    st.rerun()
#
#st.markdown("---")


# --------------------------------------------------
# AI generation
# --------------------------------------------------
st.subheader("✨ Generate AI-Adapted Lesson")
topic = st.text_input("Enter your lesson topic:")

if st.button("Generate Lesson"):
    if not topic:
        st.warning("Enter a topic first.")
    elif not can_generate:
        st.error("You can’t generate right now.")
    else:
        with st.spinner("Generating lesson..."):
            prompt = f"""
            You are an expert instructional designer.
            Using the Jigsaw, Bus Stops, and Line methods,
            create concise lesson outlines for the topic "{topic}".
            Each method: title, objective, 1–2 before activities,
            1 central activity, and 1–2 after activities.
            Keep total under 250 words.
            """
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=350,
                )
                st.markdown(resp.choices[0].message.content)

                # Update usage
                if not paid:
                    update_profile(user.id, {
                        "free_generations_used": used + 1,
                        "last_generation_date": today
                    })
            except Exception as e:
                st.error(f"API error: {e}")
