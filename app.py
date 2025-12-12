# pages/1_Methods.py
import streamlit as st
import json
import os
from datetime import date
from supabase import create_client, Client
from openai import OpenAI
from modules.languages import translations
from modules.db_operations import (
    reset_quotas_if_needed, can_generate_lesson, method_lang, safe_json_load)


st.set_page_config(page_title="Didact-io", page_icon="🧩", layout="wide")

# -------------------------------------------------------------------
# LANGUAGE SELECTION
# -------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "en"


st.sidebar.selectbox(
    "🌐 Language / Jazyk / Langue / Idioma / Sprache",
    ["en", "cs", "fr", "es", "de"],
    key="lang"
)

lang = st.session_state.lang

t = translations.get(lang, translations["en"])

def tr(key):
    return translations[st.session_state.lang].get(key, f"⚠️ Missing translation: {key}")

# -------------------------------------------------------------------
# MAIN CODE -- Methods
# -------------------------------------------------------------------

st.markdown(tr("about_short"))
st.title(tr("title"))
st.caption(tr("subtitle"))

# --- Supabase client ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

profile = {}
plan= "free"

# --- Load methods ---
@st.cache_data(ttl=300)
def load_methods():
    return supabase.table("methods").select("*").execute().data or []
methods = load_methods()

if "user" not in st.session_state:
    st.session_state.user = None

def get_quotas(plan):
    res = supabase.table("plans").select("*").eq("name", plan).execute()
    if res.data:
        return res.data[0]

quotas = get_quotas(plan)   
number_of_methods_to_show = quotas.get("weekly_method_quota")


# --- Filter methods by selected language  ---
filtered_methods = [m for m in methods if method_lang(m.get("id", "")) == lang]
filtered_methods = filtered_methods[:number_of_methods_to_show]
method_names = [m["name"] for m in filtered_methods if "id" in m]

method_qs = st.query_params.get("method", None)

# --------------------------------------------------            
# --- Render ---
# --------------------------------------------------
for m in filtered_methods:

    m_id = str(m.get("id"))
    opened = (m_id == method_qs)

    # Get translated fields with fallback
    name = m.get(f"name_{lang}") or m.get("name") or tr("unnamed_method")
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
            if st.button(tr("Hide manual") if opened else f"▶ {t['open_method']}: {name}", key=f"btn-{m_id}"):
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
            meta.append(f"**{tr('time')}:** {m['time']}")

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
            st.markdown(f"**{tr('tips')}**")

            for tip in tips:
                st.markdown(f"- {tip}")

        # Video
        if opened and m.get("videoUrl"):
            st.video(m["videoUrl"])

# Try Streamlit Cloud secrets first, then fall back to local env
api_key = st.secrets["open_AI"]["OPENAI_API_KEY"] or os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error(f"❌ {tr('no_api_key')}")
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
    return {"paid": False, "free_generations_used": 0, "last_generation_date": None, "preferred_language": "en"}

def update_profile(user_id, data: dict):
    supabase.table("profiles").update(data).eq("id", user_id).execute()

# --------------------------------------------------
# Authentication UI
# --------------------------------------------------

if not st.session_state.user:
    st.title(f"🎓 {tr('adapt_with_ai_login_title')}")
    st.info(tr("promotion_mode"))
    mode = st.radio(tr("select_to"), [tr("login"), tr("signup")], horizontal=True)
    email = st.text_input(tr("email"))
    pw = st.text_input(tr("password"), type="password")

    if mode == "Sign up":
        if st.button(tr("create_account")):
            try:
                auth_res = supabase.auth.sign_up({"email": email, "password": pw})
                if auth_res.user:
                    st.success("✅ " + tr("check_email_for_confirmation"))
                else:
                    st.error(tr("could_not_sign_up"))

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
                    st.error(tr("invalid_credentials"))

            except Exception as e:
                st.error(str(e))
    st.stop()

# --------------------------------------------------
# Logged-in area
# --------------------------------------------------
user = st.session_state.user
profile = get_profile(user.id)
plan = profile.get("plan", "free")

# Initialize language from profile ON FIRST LOGIN ONLY
if not st.session_state.get("lang_initialized", False):
    preferred = profile.get("preferred_language")
    if preferred:
        st.session_state.lang = preferred
    st.session_state.lang_initialized = True

lang = st.session_state.lang
#reset_quotas_if_needed(profile)
st.success(f"{tr('welcome')} {user.email}!")

st.sidebar.button(tr("logout"), on_click=lambda: st.session_state.pop("user"))

# Persist language change
if profile.get("preferred_language") != st.session_state.lang:
    supabase.table("profiles").update(
        {"preferred_language": st.session_state.lang}
    ).eq("id", user.id).execute()


# --------------------------------------------------
# AI generation
# --------------------------------------------------

#Manual “Pay” unlock
#if not paid and st.button("💳 Mark as Paid (Manual)"):
#    update_profile(user.id, {"paid_now": True})
#    st.rerun()

st.markdown("---")

can_generate = False
can_generate = can_generate_lesson(profile, plan)

st.subheader(f"✨ {tr('generate_AI_subheader')}:")

topic = st.text_input(f"{tr('enter_topic')}:")

method_options = {m["name"]: m["id"] for m in filtered_methods}

selected_names = st.multiselect(
    f"{tr('Choose_methods_for_AI')}:",
    list(method_options.keys()),
)

# Disable new selections when 2 are picked
if len(selected_names) >= 2:
    st.info("✅ " + tr("selected_max_two"))
    selected_names = selected_names[:2]

selected_methods = [method_options[name] for name in selected_names]

methods_steps = []

for method_id in selected_methods:
    # Find the method dict that matches the selected ID
    method_data = next((m for m in filtered_methods if m["id"] == method_id), None)

    if not method_data:
        continue

    # Load the content_md JSON (list of steps)
    content = safe_json_load(method_data.get("content_md"))

    # Convert the list of step dicts to readable strings
    if isinstance(content, list):
        content_sorted = sorted(
            content, key=lambda s: s.get("order", 0)
        )
        steps_text = "\n".join(
            f"{s.get('order', i+1)}. {s.get('title', '')}: {s.get('activity', '')}"
            for i, s in enumerate(content_sorted)
            if isinstance(s, dict)
        )
    else:
        steps_text = str(content)

    # Append a formatted version for later use in the prompt
    methods_steps.append(f"{method_data.get('name', method_names)} — {steps_text}")

# Optional: preview in Streamlit
st.markdown(f"### 🧩 {tr('selected_methods')}")
for ms in selected_methods:
    st.markdown(f"- {ms}")

# For debugging
st.write(methods_steps)

if st.button(tr("Generate Lesson")):
    if not topic:
        if not topic:
            st.warning(tr("enter_topic_first"))
    elif not can_generate:
        st.error(tr("cannot_generate_now"))

    else:
        with st.spinner(tr("generating_lesson")):
            prompt = f"""
            You are an expert instructional designer. 
            Adapt the following teaching methods to re-create lesson outlines tailored for the topic "{topic}".
            
            Methods and their ordered steps:
            {chr(10).join(methods_steps)}
                        
            For each method, provide:
            - A concise adapted title
            - One clear learning objective
            - Ordered step-by-step instructions
            - One before-activity and one after-activity
            Keep total under 280 words. Use {lang} language, unless the topic "{topic}" in another language (then use that language).
            """
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=350,
                )
                st.markdown(resp.choices[0].message.content)

                supabase.table("profiles").update(profile).eq("id", user.id).execute()

            except Exception as e:
                st.error(f"{tr('api_error')}: {e}")

