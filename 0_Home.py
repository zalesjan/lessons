import streamlit as st
import json
import os
import uuid
from datetime import date, timedelta
import time
import hashlib
from openai import OpenAI
from modules.languages import translations
from modules.db_operations import record_generation, can_generate_lesson, can_generate_guest, safe_json_load
from modules.language_manager import LanguageManager
from streamlit_cookies_manager import EncryptedCookieManager
#from streamlit_cookies_manager import CookieManager

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
# SUPABASE
# ==================================================
from supabase import create_client, ClientOptions, Client

url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

# ==================================================
# SESSION STATE INIT
# ==================================================
for k, v in {
    "ai_result": None,
    "ai_topic": None,
}.items():
    st.session_state.setdefault(k, v)
    
#  ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(page_title="Didact-io", page_icon="🧩", layout="wide")

# ==================================================
# SESSION RESTORE - COOKIES
# ==================================================

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

def restore_user_from_cookie():
    if cookies is None:
        return None, None, None

    raw = cookies.get("didact_supabase_session")
    if not raw:
        return None, None, None

    try:
        data = json.loads(raw)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token or not refresh_token:
            return None, None, None

        client = create_client(url, key)
        client.auth.set_session(access_token, refresh_token)

        session = client.auth.get_session()
        if not session or not session.user:
            return None, None, None

        # 🔐 persist refreshed tokens
        cookies["didact_supabase_session"] = json.dumps({
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        })
        cookies.save()

        user = {
            "id": session.user.id,
            "email": session.user.email,
        }

        return client, session, user

    except Exception:
        return None, None, None

COOKIE_PASSWORD = st.secrets["cookies"]["cookie_password"]
cookies = None

if COOKIE_PASSWORD:
    #cookies = CookieManager(prefix="didact")
    cookies = EncryptedCookieManager(
        prefix="didact",
        password=COOKIE_PASSWORD,
    )

if cookies is not None and not cookies.ready():
    st.info("🔄 Initializing session…")
    st.stop()

# ==================================================
# AUTH INIT (SINGLE SOURCE OF TRUTH)
# ==================================================
if "auth_loaded" not in st.session_state:
 
    client, session, user = restore_user_from_cookie()

    st.session_state.supabase = client
    st.session_state.session = session
    st.session_state.user = user

    st.session_state.auth_loaded = True

# ==================================================
# STABLE ANON ID MANAGEMENT (persistent via URL)
# ==================================================
def get_or_create_anon_id():
    """Ensure a persistent anon_id stored in URL and session_state."""
    if "anon_id" in st.session_state:
        return st.session_state.anon_id
    
    anon_id = st.query_params.get("anon_id")
    if isinstance(anon_id, list):
        anon_id = anon_id[0]

    # If missing, generate new anon_id and update URL
    if not anon_id:
        anon_id = str(uuid.uuid4())
        st.query_params["anon_id"] = anon_id
        st.query_params.update({"anon_id": anon_id})

    # Sync to session_state
    st.session_state.anon_id = anon_id
    return anon_id

anon_id = get_or_create_anon_id()

# ==================================================
# SUPABASE CLIENT FACTORIES
# ==================================================
def get_guest_client():
    """Create a Supabase client for non-authenticated guests."""
    return create_client(
        url,
        key,
        options=ClientOptions(
            headers={"x-anon-id": anon_id}  # critical for RLS policies
        ),
    )

def ensure_supabase_client():
    """Guarantee that st.session_state.supabase is a valid client."""
    if "supabase" in st.session_state and st.session_state.supabase is not None:
        return st.session_state.supabase

    # Default to guest client
    client = get_guest_client()
    st.session_state.supabase = client
    return client

def get_user_client(session):
    """Create a Supabase client for logged-in users."""
    return create_client(
        url,
        key,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {session.access_token}"}
        ),
    )

def require_user_client() -> Client:
    session = st.session_state.get("session")
    if not session:
        raise RuntimeError("Authenticated user required for this operation")

    return get_user_client(session)

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

def create_auth_client():
    return create_client(url, key)

# ==================================================
# AUTO-REFRESH SESSION (every 50 minutes)
# ==================================================
if st.session_state.get("session") and st.session_state.get("supabase"):
    last_refresh = st.session_state.get("last_refresh")
    
    if not last_refresh:
        st.session_state["last_refresh"] = time.time()
    
    elif time.time() - last_refresh > 50 * 60:
        try:
            client = st.session_state.supabase

            refresh_response = client.auth.refresh_session()

            if not refresh_response or not refresh_response.session:
                raise RuntimeError("No session returned during refresh")
            new_session = refresh_response.session
            
            # 🔥 THIS IS THE CRITICAL MISSING STEP
            client.auth.set_session(
                new_session.access_token,
                new_session.refresh_token,
            )

            st.session_state.session = new_session
            st.session_state["last_refresh"] = time.time()

            # persist refreshed tokens
            if cookies:
                cookies["didact_supabase_session"] = json.dumps({
                    "access_token": new_session.access_token,
                    "refresh_token": new_session.refresh_token,
                    "user": st.session_state.user,
                })
                cookies.save()
                st.write("🔄 Session auto-refreshed")

        except Exception as e:
            st.warning(f"⚠️ Auto-refresh failed: {e}")


# ==================================================
# INITIAL CLIENT (guest by default)
# ==================================================
if "supabase" not in st.session_state or st.session_state.supabase is None:
    if st.session_state.get("session"):
        st.session_state.supabase = get_user_client(st.session_state.session)
    else:
        st.session_state.supabase = get_guest_client()

# ==================================================
# LANGUAGE BOOTSTRAP 
# ==================================================
tr = LanguageManager.tr

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

# ==================================================
# LANGUAGE MANAGER — Initialize from URL / Profile / Session
# ==================================================

# Load profile language if logged in
if st.session_state.get("user"):
    try:
        res = ensure_supabase_client().table("profiles").select(
            "preferred_language"
        ).eq("id", st.session_state.user["id"]).single().execute()
        preferred_lang = res.data.get("preferred_language") if res.data else None
    except Exception:
        preferred_lang = None
else:
    preferred_lang = None

LanguageManager.init_language(profile_language=preferred_lang)

# helpers
lang = st.session_state.lang
tr = LanguageManager.tr

# ==================================================
# AUTH UI (LOGIN / SIGNUP)
# ==================================================
force_login = st.session_state.pop("force_login", False)

if not st.session_state.user:
    with st.sidebar.expander(f"🔐 {tr("login")} / {tr("signup")}",

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
                    client = create_auth_client()

                    res = client.auth.sign_in_with_password({
                        "email": email,
                        "password": pw
                    })

                    if res.user and res.session:
                        # 🔐 bind session to client (THIS WAS MISSING)
                        client.auth.set_session(
                            res.session.access_token,
                            res.session.refresh_token,
                        )

                        st.session_state.user = {
                            "id": res.user.id,
                            "email": res.user.email,
                        }                        
                        st.session_state.session = res.session
                        st.session_state.supabase = client

                        st.session_state.last_refresh = time.time()

                        if cookies is not None:
                            cookies["didact_supabase_session"] = json.dumps({
                                "access_token": res.session.access_token,
                                "refresh_token": res.session.refresh_token,
                            })
                            st.success("About to save cookies")
                            cookies.save()
                            
                        
                        # 🔁 post-login redirect
                        next_page = st.query_params.get("next")
                        next_page = next_page[0] if isinstance(next_page, list) else next_page

                        # 🔁 SAFE post-login redirect (preserve anon_id + others)
                        params = dict(st.query_params)

                        # keep language explicit if you want
                        params["lang"] = st.session_state.lang

                        st.query_params.update(params)

                        if next_page == "billing":
                            st.switch_page("pages/9_💳_Billing.py")
                        else:
                            st.rerun()

                except Exception as e:
                    st.error(str(e))

# ==================================================
# LANGUAGE SELECTOR (WIDGET OWNS STATE)
# ==================================================
LanguageManager.sidebar_selector()

# ==================================================
# PROFILES (READ cached, WRITE uncached ✅)
# ==================================================
@st.cache_data(ttl=900)
def load_profile(user_id):
    client = require_user_client()
    res = (
        client
        .table("profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return res.data

def load_profile_uncached(user_id):
    client = require_user_client()

    res = (
        client
        .table("profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return res.data

def ensure_profile(user_id):
    assert_not_cached_write("ensure_profile")

    client = require_user_client()

    profile = load_profile(user_id)
    if profile:
        return profile

    client.table("profiles").insert({
        "user_id": user_id,
        "preferred_language": st.session_state.lang,
        "plan": "free",
    }).execute()
    load_profile.clear()

    profile = load_profile(user_id)
    if not profile:
        raise RuntimeError(f"Profile creation failed for user {user_id}")

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
if st.session_state.user:

    try:
        profile = ensure_profile(st.session_state.user["id"])
        tier = profile["plan"]
        guest = None
    except Exception as e:
        st.error(f"Profile error: {e}")
        st.stop()

    #except Exception as e:
    #    if not st.session_state.get("user"):
    #        # only fallback to guest if user really missing
    #        profile = None
    #        guest = ensure_guest_session(anon_id)
    #        tier = "guest"
    #        st.warning("Session expired. Switched to guest mode.")
else:
    #st.warning("333.")
    guest = ensure_guest_session(anon_id)
    profile = "guest"
    tier = "guest"

# ==================================================
# PERSIST LANGUAGE CHANGES
# ==================================================
if st.session_state.user and profile:
    current_lang = st.session_state.lang
    saved_lang = profile.get("preferred_language")

    if saved_lang != current_lang:
        client = require_user_client()

        client.table("profiles").update(
            {"preferred_language": current_lang}
        ).eq(
            "user_id", st.session_state.user["id"]
        ).execute()

        # 🔥 bust cached profile so next reads are fresh
        load_profile.clear()

# ==================================================
# ENTITLEMENT & ROTATION
# ==================================================

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


    return res

supabase_client = ensure_supabase_client()
methods = load_visible_methods(supabase_client, tier, lang)
parsed_methods = []

for m in methods:
    parsed = {
        **m,  # shallow copy
        "_parsed": {
        "before": safe_json_load(m.get("before")),
        "after": safe_json_load(m.get("after")),
        "content": safe_json_load(m.get("content_md")),
        "tools": safe_json_load(m.get("tools")),
    }}
    parsed_methods.append(parsed)

# ==================================================
# UI LOGOUT
# ==================================================
if st.session_state.user:
    #st.success(f"{tr('welcome')}")

    def logout():
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.supabase = get_guest_client()
        cookies.pop("didact_supabase_session", None)
        cookies.save()
        st.query_params.clear()
        st.rerun()

    st.sidebar.button(tr("logout"), on_click=logout)

# ==================================================
# UI Header
# ==================================================
st.title(tr("title"))
if not st.session_state.user: 
    st.error(tr("log_to_use"))
st.subheader(f"🎓 {tr('adapt_with_ai_login_title1')}")
st.subheader(f"🎓 {tr('adapt_with_ai_login_title')}")
st.write(tr("subtitle"))

# ==================================================
#METHODS PAGE RENDERING (possibly move first part - titles - to UI Header)
# ==================================================

if st.session_state.user:
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

if not st.session_state.user:
    st.sidebar.error(
        f"👋 Guest daily quotas: {number_of_methods_to_show} methods visible - 3 AI adaptations\n"
        f"- Create a free account to unlock more."
    )

filtered_methods = parsed_methods[:number_of_methods_to_show]
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
                    meta.append(f"**{tr("level")}:** " + ", ".join(map(str, vals)))

            if m.get("tags"):
                        meta.append(str(m["tags"]))

            if m.get("time"):
                meta.append(f"**{tr('time')}:** {m['time']}")

            if tools:
                meta.append(f"**{tr("materials")}:** " + ", ".join(map(str, tools)))

            if meta:
                st.info(" · ".join(meta))

        # --- RIGHT: button ---
        with cols[1]:
            if st.button(
                tr("hide_manual") if opened else f"▶ {tr("open_method")}",
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

            render_steps(tr("main_method"), content)
            render_steps(tr("before"), before)
            render_steps(tr("after"), after)

            # ---------- TOOLS ----------
            if tools:
                    st.markdown(
                        f"**{tr("materials")}:** " + ", ".join(map(str, tools))
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
if st.session_state.user: 
    plan = ensure_supabase_client().table("plans").select("*").eq(
        "name", profile["plan"]
    ).single().execute().data
    can_generate, msg = can_generate_lesson(profile, plan)
else:
    guest = ensure_guest_session(anon_id)
    can_generate, msg = can_generate_guest(guest)

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
                Just say "Hi" back. it is for test.
                """
                #prompt = f"""
                #You are an expert instructional designer. 
                #Adapt the following teaching methods to re-create lesson outlines tailored for the topic "{topic}".
                #
                #Methods and their ordered steps:
                #{chr(10).join(methods_steps)}
                #            
                #For each method, provide:
                #- A concise adapted title
                #- One clear learning objective
                #- Ordered step-by-step instructions
                #- One before-activity and one after-activity
                #Keep total under 280 words. Use {lang} language, unless the topic "{topic}" in another language (then use that language).
                #"""
                try:
                    resp = client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=450,
                    )
                    st.session_state.ai_result = resp.choices[0].message.content
                    st.session_state.ai_topic = topic
                    
                    if st.session_state.user:
                        fresh_profile = load_profile_uncached(st.session_state.user["id"])
                        updated_profile = record_generation(fresh_profile)
                        #st.write(updated_profile)

                        try:
                            ensure_supabase_client().table("profiles").update(updated_profile).eq(
                                "id", st.session_state.user["id"]
                            ).execute()
                        except Exception as e:
                            st.error(f"{tr('update?error!!!!!!!')}: {e}")
                    else:
                        load_guest_session.clear()
                        # Always pull the latest data to avoid stale cached values
                        resp = ensure_supabase_client().table("guest_sessions") \
                            .select("*").eq("anon_id", anon_id).single().execute()
                        guest_data = resp.data or {}

                        # Safely handle missing or null fields
                        lessons_generated = (guest_data.get("lessons_generated") or 0) + 1
                        ai_used_week = (guest_data.get("ai_used_week") or 0) + 1
                        ai_used_month = (guest_data.get("ai_used_month") or 0) + 1

                        # Optionally keep week/month start fields consistent
                        week_start = guest_data.get("week_start") or date.today().isoformat()
                        month_start = guest_data.get("month_start") or date.today().replace(day=1).isoformat()

                        update_data = {
                            "lessons_generated": lessons_generated,
                            "ai_used_week": ai_used_week,
                            "ai_used_month": ai_used_month,
                            "last_generated_at": "now()",
                            "week_start": week_start,
                            "month_start": month_start,
                        }

                        result = ensure_supabase_client().table("guest_sessions") \
                            .update(update_data).eq("anon_id", anon_id).execute()

                        #st.write("✅ Update result:", result.data)
                        #st.write("Before update:", guest_data)
                        #st.write("Sending update:", update_data)

                except Exception as e:
                    st.error(f"{tr('api_error!!!!!!!')}: {e}")
                    

if st.session_state.ai_result:
    st.markdown("---")
    #st.subheader(f"✨ {tr('generated_lesson')}")
    if st.session_state.ai_topic:
        st.caption(f"🧠 {st.session_state.ai_topic}")

    st.markdown(st.session_state.ai_result)

# ==================================================
# PERIOD RESET (moved here to avoid overwriting AI counters)
# ==================================================
if not st.session_state.user:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    current_week_start = monday.isoformat()
    current_month_start = today.replace(day=1).isoformat()

    resp = ensure_supabase_client().table("guest_sessions") \
        .select("ai_used_week, ai_used_month, week_start, month_start") \
        .eq("anon_id", anon_id).single().execute()
    guest_data = resp.data or {}

    should_reset_week = guest_data.get("week_start") != current_week_start
    should_reset_month = guest_data.get("month_start") != current_month_start

    update_fields = {}
    if should_reset_week and guest_data.get("ai_used_week", 0) != 0:
        update_fields["ai_used_week"] = 0
    if should_reset_month and guest_data.get("ai_used_month", 0) != 0:
        update_fields["ai_used_month"] = 0
    if should_reset_week or should_reset_month:
        update_fields["week_start"] = current_week_start
        update_fields["month_start"] = current_month_start
        ensure_supabase_client().table("guest_sessions") \
            .update(update_fields).eq("anon_id", anon_id).execute()
