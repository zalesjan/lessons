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
from modules.db_operations import record_generation, can_generate_lesson, can_generate_guest, safe_json_load
from streamlit_cookies_manager import EncryptedCookieManager

# ==================================================
# CACHE DEBUG (🧪 TURN OFF IN PROD IF YOU WANT)
# ==================================================
CACHE_DEBUG = True

def assert_not_cached_write(func_name: str):
    """
    Guard against accidentally caching write functions.
    """
    if CACHE_DEBUG and getattr(st, "_is_running_with_streamlit", False):
        # If this function ever gets wrapped by cache, explode early
        if hasattr(globals().get(func_name), "__wrapped__"):
            raise RuntimeError(
                f"❌ Cache misuse detected: `{func_name}` must NEVER be cached."
            )
        
# ==================================================
# cookies
# ==================================================
COOKIE_PASSWORD = st.secrets.get("cookies", {}).get("cookie_password")
cookies = None

if COOKIE_PASSWORD:
    cookies = EncryptedCookieManager(
        prefix="didact",
        password=COOKIE_PASSWORD,
    )
    if not cookies.ready():
        st.stop()

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(page_title="Didact-io", page_icon="🧩", layout="wide")

ALLOWED_LANGS = ["en", "cs", "fr", "es", "de"]

# ==================================================
# SUPABASE
# ==================================================
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

if "anon_id" not in st.session_state:
    st.session_state.anon_id = str(uuid.uuid4())

anon_id = st.session_state.anon_id

def ensure_supabase_client():
    """
    Guarantee that st.session_state.supabase is a valid client.
    """
    if st.session_state.supabase is not None:
        return st.session_state.supabase

    # Fallback: guest client
    client = get_guest_client()
    st.session_state.supabase = client
    return client

# ==================================================
# SUPABASE CLIENT FACTORIES
# ==================================================
def get_guest_client():
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

# ==================================================
# SESSION STATE INIT
# ==================================================
for k, v in {
    "user": None,
    "session": None,
    "supabase": None,
    #"about_mode": None,
    "ai_result": None,
    "ai_topic": None,
}.items():
    st.session_state.setdefault(k, v)

def normalize_user(user):
    """
    Ensure user is always a dict with at least {id, email}.
    """
    if user is None:
        return None

    # Supabase User object
    if hasattr(user, "id"):
        return {
            "id": user.id,
            "email": user.email,
        }

    # Already normalized
    if isinstance(user, dict):
        return user

    raise TypeError(f"Unsupported user type: {type(user)}")

# 🔁 RESTORE SESSION FROM COOKIE
if cookies and st.session_state.user is None and cookies.get("supabase_session"):
    session_data = json.loads(cookies["supabase_session"])

    access_token = session_data.get("access_token")
    refresh_token = session_data.get("refresh_token")
    user_data = session_data.get("user")
    
    # Create a temporary client to restore session
    client = get_guest_client()

    try:
        # 🔑 This refreshes the JWT if expired
        new_session = client.auth.set_session(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        st.session_state.user = normalize_user(user_data)
        st.session_state.session = new_session
        st.session_state.supabase = get_user_client_cached(
            new_session.access_token
        )
        # 🔁 Persist refreshed tokens
        cookies["supabase_session"] = json.dumps({
            "access_token": new_session.access_token,
            "refresh_token": new_session.refresh_token,
            "user": user_data,
        })
        cookies.save()
    
    except Exception:
        cookies.pop("supabase_session", None)
        cookies.save()
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.supabase = get_guest_client()
  

# ==================================================
# INITIAL CLIENT (guest by default)
# ==================================================
if "supabase" not in st.session_state:
    st.session_state.supabase = get_guest_client()

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
        res = ensure_supabase_client().table("profiles").select(
            "preferred_language"
        ).eq("id", st.session_state.user["id"]).execute()
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

# --------------------------------------------------
# LOGIN INTENT (PERSISTED)
# --------------------------------------------------
action = st.query_params.get("action")
action = action[0] if isinstance(action, list) else action

if action == "login":
    st.session_state.force_login = True

# ==================================================
# AUTH STATE
# ==================================================
if "user" not in st.session_state:
    st.session_state.user = None

if "session" not in st.session_state:
    st.session_state.session = None
#
#
# MAYBE CAN BE REMOVED
action = st.query_params.get("action")
action = action[0] if isinstance(action, list) else action

#if "about_mode" not in st.session_state:
#    st.session_state.about_mode = None

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
                    res = ensure_supabase_client().auth.sign_up(
                        {"email": email, "password": pw}
                    )
                    if res.user:
                        st.success(tr("check_email_for_confirmation"))
                except Exception as e:
                    st.error(str(e))
        else:
            if st.button(tr("login"), key="login_btn"):
                try:
                    res = ensure_supabase_client().auth.sign_in_with_password(
                        {"email": email, "password": pw}
                    )
                    if res.user:
                        st.session_state.user = normalize_user(res.user)
                        st.session_state.session = res.session

                        # 🔥 switch to user client
                        st.session_state.supabase = get_user_client_cached(res.session)

                        if cookies:
                            cookies["supabase_session"] = json.dumps({
                                "access_token": res.session.access_token,
                                "refresh_token": res.session.refresh_token,
                                "user": {
                                    "id": res.user["id"],
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
# PROFILES (READ cached, WRITE uncached ✅)
# ==================================================
@st.cache_data(ttl=300)
def load_profile(user_id):
    res = ensure_supabase_client().table("profiles").select("*").eq(
        "user_id", user_id
    ).execute()
    return res.data[0] if res.data else None

def ensure_profile(user_id):
    assert_not_cached_write("ensure_profile")

    profile = load_profile(user_id)
    if profile:
        return profile

    try:
        ensure_supabase_client().table("profiles").insert({
            "user_id": user_id,
            "preferred_language": lang,
            "plan": "free",
        }).execute()
    except Exception as e:
        raise RuntimeError(
            f"Failed to create profile for user {user_id}: {e}"
        )

    load_profile.clear()
    profile = load_profile(user_id)

    if not profile:
        raise RuntimeError(
            f"Profile still missing after insert for user {user_id}"
        )

    return profile


# ==================================================
# GUEST SESSIONS (READ cached, WRITE uncached ✅)
# ==================================================
@st.cache_data(ttl=300)
def load_guest_session(anon_id):
    res = (
        get_guest_client()
        .table("guest_sessions")
        .select("*")
        .eq("anon_id", anon_id)
        .execute()
    )
    return res.data[0] if res.data else None

def ensure_guest_session(anon_id):
    assert_not_cached_write("ensure_guest_session")

    guest = load_guest_session(anon_id)
    if guest:
        return guest

    get_guest_client().table("guest_sessions").insert({
        "anon_id": anon_id
    }).execute()

    load_guest_session.clear()
    return load_guest_session(anon_id)

# ==================================================
# LOGGED-IN AREA
# ==================================================
user = st.session_state.user

if user:
    try:
        profile = ensure_profile(user["id"])
        tier = profile["plan"]
        guest = None
    except Exception as e:
        # auth is broken → reset to guest safely
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.supabase = get_guest_client()
        profile = None
        guest = ensure_guest_session(anon_id)
        tier = "guest"
        st.warning("Session expired. Switched to guest mode.")
else:
    profile = "guest"
    guest = ensure_guest_session(anon_id)
    tier = "guest"

# ==================================================
# PERSIST LANGUAGE CHANGES
# ==================================================
if user and profile.get("preferred_language") != st.session_state.lang:
    ensure_supabase_client().table("profiles").update(
        {"preferred_language": st.session_state.lang}
    ).eq("id", user["id"]).execute()

# ==================================================
# ENTITLEMENT & ROTATION
# ==================================================
#def compute_bucket(seed, modulo=3):
#    h = hashlib.sha256(seed.encode()).hexdigest()
#    return int(h, 16) % modulo

#bucket = compute_bucket(user["id"] if user else anon_id)

@st.cache_data(ttl=300)
def load_visible_methods(_supabase_client, tier: str, lang: str):
    if _supabase_client is None:
        raise RuntimeError("Supabase client is None in load_visible_methods")
    
    today = date.today().isoformat()

    ids = [
        r["method_id"]
        for r in _supabase_client.table("method_visibility")
        .select("method_id")
        .eq("tier", tier)
        .lte("valid_from", today)
        .gte("valid_to", today)
        .execute()
        .data
    ]

    if not ids:
        return []

    res = (
        _supabase_client.table("methods")
        .select("*")
        .eq("language_code", lang)
        .in_("id", ids)
        .execute()
        .data
    )

    if not res and lang != "en":
        res = (
            _supabase_client.table("methods")
            .select("*")
            .eq("language_code", "en")
            .in_("id", ids)
            .execute()
            .data
        )

    # parse JSON once
    for m in res:
        m["_parsed"] = {
            "before": safe_json_load(m.get("before")),
            "after": safe_json_load(m.get("after")),
            "content": safe_json_load(m.get("content_md")),
            "tools": safe_json_load(m.get("tools")),
        }

    return res

supabase_client = ensure_supabase_client()
methods = load_visible_methods(supabase_client, tier, lang)

# ==================================================
# UI LOGOUT
# ==================================================
if user:
    #st.success(f"{tr('welcome')} {user.email}")

    def logout():
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.supabase = get_guest_client()
        cookies.pop("supabase_session", None)
        cookies.save()
        st.query_params.clear()
        st.rerun()

    st.sidebar.button(tr("logout"), on_click=logout)

# ==================================================
# UI Header
# ==================================================
st.title(f"🎓 {tr('adapt_with_ai_login_title1')}")
st.title(f"🎓 {tr('adapt_with_ai_login_title')}")
if not user: 
    st.error(tr("log_to_use"))

# ==================================================
#METHODS PAGE RENDERING (possibly move first part - titles - to UI Header)
# ==================================================
st.title(tr("title"))
st.write(tr("subtitle"))

if user:
    plan_name = profile["plan"]
else:
    plan_name = "guest"

plan = (
        ensure_supabase_client().table("plans")
        .select("*")
        .eq("name", plan_name)
        .single()
        .execute()
        .data
    )
number_of_methods_to_show = plan["weekly_method_quota"]

if not user:
    st.sidebar.error(
        f"👋 Guest daily quotas: {number_of_methods_to_show} methods visible - 3 AI adaptations\n"
        f"- Create a free account to unlock more."
    )

filtered_methods = methods[:number_of_methods_to_show]
method_names = [m["name"] for m in filtered_methods if "id" in m]

method_qs = st.query_params.get("method", None)
method_qs = method_qs[0] if isinstance(method_qs, list) else method_qs

# Auto-collapse About when a method is opened
#if method_qs:
#    st.session_state.about_mode = None
# --------------------------------------------------            
# --- Render ---
# --------------------------------------------------
for m in filtered_methods:

    m_id = str(m.get("id"))
    opened = (m_id == method_qs)

    # Get translated fields with fallback
    name = m.get(f"name_{lang}") or m.get("name") or tr("unnamed_method")
    description = m.get(f"description{lang}") or m.get("description")
    tips = m.get(f"tips_{lang}") or m.get("tips")

    before = safe_json_load(m["before"])
    after = safe_json_load(m["after"])
    content = safe_json_load(m["content_md"])
    
    # ---- Parsed JSON (single source of truth) ----
    parsed = m.get("_parsed", {})
    before = parsed.get("before") or []
    after = parsed.get("after") or []
    content = parsed.get("content") or []
    tools = parsed.get("tools") or []

    with st.container(border=True):
        cols = st.columns([0.7, 0.3])

        # ================= LEFT =================
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

            if tools:
                meta.append(f"**{t['materials']}:** " + ", ".join(map(str, tools)))

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
            def render_steps(title, steps):
                if not steps:
                    return
                st.markdown(f"##### {title}")
                for step in sorted(steps, key=lambda x: x.get("order", 0)):
                    mins = (
                        f" — {step['minutes']} min"
                        if step.get("minutes")
                        else ""
                    )
                    st.markdown(
                        f"- **{step.get('title','')}**{mins}  \n"
                        f"{step.get('activity','')}"
                    )

            render_steps(t["main_method"], content)
            render_steps(t["before"], before)
            render_steps(t["after"], after)

            # ---------- TOOLS ----------
            if tools:
                    st.markdown(
                        f"**{t['materials']}:** " + ", ".join(map(str, tools))
                    )

            # ---------- TIPS ----------
            if tips:
                tips_list = json.loads(tips) if isinstance(tips, str) else tips
                st.markdown(f"**{tr('tips')}**")
                for tip in tips_list:
                    st.markdown(f"- {tip}")

            # ---------- VIDEO ----------
            #if m.get("videoUrl"):
            #    st.video(m["videoUrl"])

# ==================================================
# AI GENERATION
# ==================================================

def rate_limit(key, seconds):
    now = time.time()
    last = st.session_state.get(key)
    if last and now - last < seconds:
        return False
    st.session_state[key] = now
    return True

st.markdown("---")
st.subheader(f"✨ {tr('generate_AI_subheader')}")

# can_generate=function in db_operations.py, 
# it compares quotas from profile table with used-up
if user: 
    plan = ensure_supabase_client().table("plans").select("*").eq(
        "name", profile["plan"]
    ).single().execute().data
    can_generate, msg = can_generate_lesson(profile, plan)
else:
    guest = ensure_guest_session(anon_id)
    can_generate, msg = can_generate_guest(guest)

    # persist resets (only if periods changed)
    ensure_supabase_client().table("guest_sessions").update({
    "ai_used_week": guest["ai_used_week"],
    "ai_used_month": guest["ai_used_month"],
    "week_start": guest["week_start"].isoformat() if guest["week_start"] else None,
    "month_start": guest["month_start"].isoformat() if guest["month_start"] else None,
}).eq("anon_id", anon_id).execute()

    if msg:
        msg = tr("guest_limit_reached")
        st.error(msg)
        st.stop()
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

if selected_names:
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
    #st.markdown(f"### 🧩 {tr('selected_methods')}")
    #for ms in selected_methods:
    #    st.markdown(f"- {ms}")

    if st.button(tr("generate_button")):
        if not topic:
            st.warning(tr("enter_topic_first"))
        elif not can_generate:
            st.error(tr("cannot_generate_now"))
            st.stop()
        elif not rate_limit("ai_rate", 30):
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
                        max_tokens=450,
                    )
                    st.session_state.ai_result = resp.choices[0].message.content
                    st.session_state.ai_topic = topic

                    if user:
                        profile = record_generation(profile)
                        ensure_supabase_client().table("profiles").update(profile).eq(
                            "id", user["id"]
                        ).execute()
                    else:
                        ensure_supabase_client().table("guest_sessions").update({
                            "lessons_generated": guest["lessons_generated"] + 1,
                            "ai_used_week": guest["ai_used_week"] + 1,
                            "ai_used_month": guest["ai_used_month"] + 1,
                            "last_generated_at": "now()"
                        }).eq("anon_id", anon_id).execute()

                except Exception as e:
                    st.error(f"{tr('api_error')}: {e}")

if st.session_state.ai_result:
    st.markdown("---")
    #st.subheader(f"✨ {tr('generated_lesson')}")
    if st.session_state.ai_topic:
        st.caption(f"🧠 {st.session_state.ai_topic}")

    st.markdown(st.session_state.ai_result)


