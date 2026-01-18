# pages/1_Methods.py
import streamlit as st
import json
import os
import uuid
from datetime import date
import time
import hashlib
from supabase import create_client, ClientOptions, Client
from openai import OpenAI
from modules.languages import translations
from modules.db_operations import record_generation, can_generate_lesson, safe_json_load
from streamlit_cookies_manager import EncryptedCookieManager

# ==================================================
# cookies
# ==================================================
cookies = EncryptedCookieManager(
    prefix="didact",
    password=st.secrets["cookies"]["cookie_password"],  # add to secrets.toml
)

if not cookies.ready():
    st.stop()
# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(page_title="Didact-io", page_icon="🧩", layout="wide")

GUEST_METHODS_VISIBLE = 5
GUEST_AI_GENERATIONS = 1
GUEST_AI_RATE_LIMIT_SEC = 30

ALLOWED_LANGS = ["en", "cs", "fr", "es", "de"]
# ==================================================
# SUPABASE
# ==================================================
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

if "anon_id" not in st.session_state:
    st.session_state.anon_id = str(uuid.uuid4())

anon_id = st.session_state.anon_id

# ==================================================
# SUPABASE CLIENT FACTORIES
# ==================================================
@st.cache_resource
def get_guest_client_cached():
    return create_client(
        url,
        key,
        options=ClientOptions(
            headers={"x-anon-id": anon_id}
        )
    )

@st.cache_resource
def get_user_client_cached(session):
    return create_client(
        url,
        key,
        options=ClientOptions(
            headers={
                "Authorization": f"Bearer {session.access_token}"
            }
        )
    )
# =============================================
# Restore session on app start (CRITICAL FIX)
# -============================================
if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None

# 🔁 RESTORE SESSION FROM COOKIE
if st.session_state.user is None and cookies.get("supabase_session"):
    session_data = json.loads(cookies["supabase_session"])
    st.session_state.session = session_data
    st.session_state.user = session_data["user"]
    st.session_state.supabase = get_user_client_cached(
        type("Session", (), {"access_token": session_data["access_token"]})
    )

# --------------------------------------------------
# LOGIN INTENT (PERSISTED)
# --------------------------------------------------
action = st.query_params.get("action")
action = action[0] if isinstance(action, list) else action

if action == "login":
    st.session_state.force_login = True

# ==================================================
# INITIAL CLIENT (guest by default)
# ==================================================
if "supabase" not in st.session_state:
    st.session_state.supabase = get_guest_client_cached()

supabase = st.session_state.supabase

# ==================================================
# AUTH STATE
# ==================================================
if "user" not in st.session_state:
    st.session_state.user = None

if "session" not in st.session_state:
    st.session_state.session = None

action = st.query_params.get("action")
action = action[0] if isinstance(action, list) else action

if "about_mode" not in st.session_state:
    st.session_state.about_mode = None

# ==================================================
# LANGUAGE BOOTSTRAP 
# ==================================================
query_lang = st.query_params.get("lang")
if isinstance(query_lang, list):
    query_lang = query_lang[0]

# Default
initial_lang = "en"

# URL has priority
if query_lang in ["en", "cs", "fr", "es", "de"]:
    initial_lang = query_lang

# If logged in already, profile may exist
elif st.session_state.get("user"):
    try:
        res = supabase.table("profiles").select(
            "preferred_language"
        ).eq("id", st.session_state.user.id).execute()
        if res.data and res.data[0].get("preferred_language"):
            initial_lang = res.data[0]["preferred_language"]
    except Exception:
        pass

# Initialize ONCE, before widget
if "lang" not in st.session_state:
    st.session_state.lang = initial_lang

lang = st.session_state.lang
t = translations.get(lang, translations["en"])

def tr(key: str) -> str:
    return translations[lang].get(key, f"⚠️ Missing translation: {key}")
# ==================================================
# AUTH UI (LOGIN / SIGNUP)
# ==================================================
force_login = st.session_state.pop("force_login", False)

if not st.session_state.user:
    with st.sidebar.expander("🔐 Login / Sign up",
        expanded=force_login
    ):
        
        #st.info(tr("promotion_mode"))

        mode = st.radio(
            tr("select_to"),
            [tr("login"), tr("signup")],
            horizontal=True,
        )

        email = st.text_input(tr("email"))
        pw = st.text_input(tr("password"), type="password")

        if mode == tr("signup"):
            if st.button(tr("create_account")):
                try:
                    res = supabase.auth.sign_up(
                        {"email": email, "password": pw}
                    )
                    if res.user:
                        st.success(tr("check_email_for_confirmation"))
                except Exception as e:
                    st.error(str(e))
        else:
            if st.button(tr("login"), key="login_btn"):
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email, "password": pw}
                    )
                    if res.user:
                        st.session_state.user = res.user
                        st.session_state.session = res.session

                        # 🔥 switch to user client
                        st.session_state.supabase = get_user_client_cached(res.session)

                        cookies["supabase_session"] = json.dumps({
                            "access_token": res.session.access_token,
                            "user": {
                                "id": res.user.id,
                                "email": res.user.email,
                            },
                        })
                        cookies.save()

                        # 🔁 post-login redirect
                        next_page = st.query_params.get("next")
                        next_page = next_page[0] if isinstance(next_page, list) else next_page

                        st.query_params.clear()

                        if next_page == "billing":
                            st.switch_page("pages/9_💳_Billing.py")
                        else:
                            st.rerun()

                except Exception as e:
                    st.error(str(e))

# ==================================================
# LANGUAGE SELECTOR (WIDGET OWNS STATE)
# ==================================================
st.sidebar.selectbox(
    "🌐 Language / Jazyk / Langue / Idioma / Sprache",
    ["en", "cs", "fr", "es", "de"],
    key="lang",
)
    
# ==================================================
# LOGGED-IN AREA
# ==================================================
user = st.session_state.user

if user:
    st.sidebar.badge(f"👋 {user.email}")

@st.cache_data(ttl=300)
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if res.data:
        return res.data[0]

    supabase.table("profiles").insert(
        {
            "user_id": user_id,
            "preferred_language": st.session_state.lang,
            "plan": "free",
        }
    ).execute()

    return {
        "user_id": user_id,
        "preferred_language": st.session_state.lang,
        "plan": "free",
    }

@st.cache_data(ttl=300)
def get_guest():
    # 🔐 ALWAYS use guest client for guest data
    guest_supabase = get_guest_client_cached()

    res = (
        guest_supabase
        .table("guest_sessions")
        .select("*")
        .eq("anon_id", anon_id)
        .execute()
    )

    if res.data:
        return res.data[0]

    guest_supabase.table("guest_sessions").insert({
        "anon_id": anon_id
    }).execute()

    return {"lessons_generated": 0}

if user:
    profile = get_profile(user.id)
    plan_name = profile.get("plan", "free")
    guest = None
else:
    profile = None
    plan_name = "guest"
    guest = get_guest()

# ==================================================
# PERSIST LANGUAGE CHANGES
# ==================================================
if user and profile.get("preferred_language") != st.session_state.lang:
    supabase.table("profiles").update(
        {"preferred_language": st.session_state.lang}
    ).eq("id", user.id).execute()

# ==================================================
# ENTITLEMENT & ROTATION
# ==================================================
#def compute_bucket(seed, modulo=3):
#    h = hashlib.sha256(seed.encode()).hexdigest()
#    return int(h, 16) % modulo

tier = profile["plan"] if user else "guest"
#bucket = compute_bucket(user.id if user else anon_id)
@st.cache_data(ttl=300)
def load_visible_methods():
    today = date.today().isoformat()

    res = (
        supabase.table("method_visibility")
        .select("method_id")
        .eq("tier", tier)
        .lte("valid_from", today)
        .gte("valid_to", today)
        .execute()
    )

    ids = [r["method_id"] for r in res.data]
    if not ids:
        return []

    # 1️⃣ Try selected language first
    methods = (
        supabase.table("methods")
        .select("*")
        .eq("language_code", lang)
        .in_("id", ids)
        .execute()
        .data
    )

    # 2️⃣ Fallback to English if none found
    if not methods and lang != "en":
        methods = (
            supabase.table("methods")
            .select("*")
            .eq("language_code", "en")
            .in_("id", ids)
            .execute()
            .data
        )

    return methods

methods = load_visible_methods()

# ==================================================
# UI HEADER
# ==================================================
if user:
    #st.success(f"{tr('welcome')} {user.email}")

    def logout():
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.supabase = get_guest_client_cached()
        cookies.pop("supabase_session", None)
        cookies.save()
        st.query_params.clear()
        st.rerun()

    st.sidebar.button(tr("logout"), on_click=logout)

if not user:
    st.error(
        f"👋 Guest mode: {GUEST_METHODS_VISIBLE} methods visible - {GUEST_AI_GENERATIONS} AI adaptations\n"
        f"- Create a free account to unlock more."
    )

# ==================================================
# LOAD PLAN
# ==================================================
if user:
    plan = (
        supabase.table("plans")
        .select("*")
        .eq("name", plan_name)
        .single()
        .execute()
        .data
    )
else:
    plan = None

# ==================================================
# UI Header
# ==================================================
st.title(f"🎓 {tr('adapt_with_ai_login_title1')}")
st.title(f"🎓 {tr('adapt_with_ai_login_title')}")
if not user: 
    st.error(tr("log_to_use"))

# ==================================================
# ABOUT SECTION
# ==================================================
def toggle_about(mode):
    st.session_state.about_mode = (
        None if st.session_state.about_mode == mode else mode
    )
    
cols = st.columns(2)

with cols[0]:
    if st.button(tr("about_short_btn")):
        toggle_about("short")

with cols[1]:
    if st.button(tr("about_full_btn")):
        toggle_about("full")

if st.session_state.about_mode == "short":
    st.info(tr("about_short"))

elif st.session_state.about_mode == "full":
    st.info(tr("about_full"))

# ==================================================
#METHODS PAGE RENDERING (possibly move first part - titles - to UI Header)
# ==================================================
st.title(tr("title"))
st.write(tr("subtitle"))

#######
visible = (
    methods[:GUEST_METHODS_VISIBLE]
    if not user else methods
)
#######

if user:
    quotas = plan
    number_of_methods_to_show = quotas.get("weekly_method_quota")
else:
    number_of_methods_to_show = GUEST_METHODS_VISIBLE
# --- Filter methods by selected language  ---
#filtered_methods = [m for m in visible if method_lang(m.get("id", "")) == lang]
#filtered_methods = filtered_methods[:number_of_methods_to_show]
filtered_methods = visible[:number_of_methods_to_show]
method_names = [m["name"] for m in filtered_methods if "id" in m]
method_qs = st.query_params.get("method", None)
method_qs = method_qs[0] if isinstance(method_qs, list) else method_qs

# Auto-collapse About when a method is opened
if method_qs:
    st.session_state.about_mode = None
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
                st.info(" · ".join(meta))

        # --- RIGHT: button ---
        with cols[1]:
            if st.button(
                tr("Hide manual") if opened else f"▶ {t['open_method']}",
                key=f"btn-{m_id}"
            ):
                if opened:
                    st.query_params.clear()
                else:
                    st.query_params["method"] = m_id

                st.rerun()
                
        if opened:
            # ---------- MAIN CONTENT ----------
            if content:
                st.markdown(f"##### {t['main_method']}")
                for step in sorted(content, key=lambda x: x.get("order", 0)):
                    title = step.get("title", "")
                    activity = step.get("activity", "")
                    minutes = step.get("minutes")
                    mins = f" — {minutes} min" if minutes else ""
                    st.markdown(f"- **{title}**{mins}  \n  {activity}")
            
            # ---------- BEFORE ----------
            if before:
                st.markdown(f"##### {t['before']}")
                for step in sorted(before, key=lambda x: x.get("order", 0)):
                    title = step.get("title", "")
                    activity = step.get("activity", "")
                    minutes = step.get("minutes")
                    mins = f" — {minutes} min" if minutes else ""
                    st.markdown(f"- **{title}**{mins}  \n  {activity}")
            
            # ---------- AFTER ----------
            if after:
                st.markdown(f"##### {t['after']}")
                for step in sorted(after, key=lambda x: x.get("order", 0)):
                    title = step.get("title", "")
                    activity = step.get("activity", "")
                    minutes = step.get("minutes")
                    mins = f" — {minutes} min" if minutes else ""
                    st.markdown(f"- **{title}**{mins}  \n  {activity}")

            # ---------- TOOLS ----------
            if m.get("tools"):
                mats = safe_json_load(m["tools"])
                if mats:
                    st.markdown(
                        f"**{t['materials']}:** " + ", ".join(map(str, mats))
                    )

            # ---------- TIPS ----------
            if tips:
                tips = json.loads(tips) if isinstance(tips, str) else tips
                st.markdown(f"**{tr('tips')}**")
                for tip in tips:
                    st.markdown(f"- {tip}")

            # ---------- VIDEO ----------
            #if m.get("videoUrl"):
            #    st.video(m["videoUrl"])

# ==================================================
# AI GENERATION (UNCHANGED)
# ==================================================

st.markdown("---")
st.subheader(f"✨ {tr('generate_AI_subheader')}")

def rate_limit(key, seconds):
    now = time.time()
    last = st.session_state.get(key)
    if last and now - last < seconds:
        return False
    st.session_state[key] = now
    return True

# can_generate=function in db_operations.py, 
# it compares quotas from profile table with used-up
if user:
    plan = supabase.table("plans").select("*").eq(
        "name", profile["plan"]
    ).single().execute().data
    can_generate, msg = can_generate_lesson(profile, plan)
else:
    can_generate = guest["lessons_generated"] < GUEST_AI_GENERATIONS
    msg = tr("guest_limit_reached")

topic = st.text_input(tr("enter_topic"))    

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

if selected_names:
    # Optional: preview in Streamlit
    st.markdown(f"### 🧩 {tr('selected_methods')}")
    for ms in selected_methods:
        st.markdown(f"- {ms}")

    if st.button(tr("generate_button")):
        if not topic:
            st.warning(tr("enter_topic_first"))
        elif not can_generate:
            st.error(tr("cannot_generate_now"))
            st.stop()
        elif not rate_limit("ai_rate", GUEST_AI_RATE_LIMIT_SEC):
            st.warning(tr("slow_down"))
            st.stop()

        else:
            api_key = (
                st.secrets["open_AI"]["OPENAI_API_KEY"]
                or os.getenv("OPENAI_API_KEY"))

            if not api_key:
                st.error(f"❌ {tr('no_api_key')}")
            else:
                client = OpenAI(api_key=api_key)
                MODEL = "gpt-4o-mini"

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

                    if user:
                        profile = record_generation(profile)
                        supabase.table("profiles").update(profile).eq(
                            "id", user.id
                        ).execute()
                    else:
                        supabase.table("guest_sessions").update({
                            "lessons_generated": guest["lessons_generated"] + 1
                        }).eq("anon_id", anon_id).execute()

                except Exception as e:
                    st.error(f"{tr('api_error')}: {e}")

