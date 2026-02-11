import streamlit as st
import requests
from modules.languages import translations
from modules.supabase_client import get_guest_client
from modules.supabase_client import get_user_client

# ==================================================
# STATE + CONFIG
# ==================================================
if "selected_interval" not in st.session_state:
    st.session_state.selected_interval = None

if "user" not in st.session_state:
    st.session_state.user = None

if "session" not in st.session_state:
    st.session_state.session = None

st.set_page_config(page_title="Billing", page_icon="💳")

# --------------------------------------------------
# Language (reuse app.py state)
# --------------------------------------------------
lang = st.session_state.get("lang", "en")

def tr(key: str) -> str:
    return translations[lang].get(key, key)

# --------------------------------------------------
# Page header
# --------------------------------------------------
st.title(tr("billing_title"))
st.markdown(tr("billing_intro"))
#st.title("💳 Upgrade to Didact.io Pro plan")
st.badge(
    """
    Upgrade your **Didact.io** account to unlock deeper access to effective
    teaching methods and and higher usage limits on AI-assisted lesson preparation.
    """
)

# --------------------------------------------------
# Safety checks
# --------------------------------------------------
if not st.session_state.user or not st.session_state.session:

    st.info(
        "🔐 **" + tr("billing_login_required_title") + "**\n\n"
        + tr("billing_login_required_text")
    )

    if st.button(tr("billing_login_cta")):
        st.query_params.update({
        "action": "login",
        "next": "billing"
        })

        st.session_state.force_login = True
        st.switch_page("app.py")

        st.stop()

# --------------------------------------------------
# Load user profile (REQUIRED for billing)
# --------------------------------------------------
if st.session_state.user:
    user_supabase = get_user_client(st.session_state.session)

    profile_res = (
        user_supabase
        .table("profiles")
        .select("*")
        .eq("user_id", st.session_state.user.id)
        .single()
        .execute()
    )

    profile = profile_res.data

    if not profile:
        st.error("User profile not initialized. Please reload the app.")
        st.stop()

# --------------------------------------------------
# Load plans from Supabase
# --------------------------------------------------
anon_supabase = get_guest_client()

plans = (
    anon_supabase
    .table("plans")
    .select("*")
    .execute()
    .data
)

if not plans:
    st.error(tr("billing_no_plans"))
    st.stop()

def render_limit(value):
    """
    Render numeric limits or ∞ with tooltip for unlimited.
    """
    if value is None:
        return (
            "<span title='Unlimited' "
            "style='cursor:help;font-size:1.1rem'>∞</span>"
        )
    return f"<span>{value}</span>"

# ==================================================
# FEATURE MATRIX (THIS FIXES YOUR ISSUE)
# ==================================================
FEATURE_ROWS = [
    {
        "label": tr("billing_feature_price"),
        "icon": "💰",
        "render": lambda plan: (
            f"<span style='font-weight:600'>{plan['price']}</span>"
        ),
    },

    # ── AI limits ──────────────────────────────────
    {
        "label": tr("billing_feature_ai_daily"),
        "icon": "🤖",
        "render": lambda plan: render_limit(
            plan.get("daily_lesson_quota")
        ),
    },
    {
        "label": tr("billing_feature_ai_weekly"),
        "icon": "🤖",
        "render": lambda plan: render_limit(
            plan.get("weekly_lesson_quota")
        ),
    },
    {
        "label": tr("billing_feature_ai_monthly"),
        "icon": "🤖",
        "render": lambda plan: render_limit(
            plan.get("monthly_lesson_quota")
        ),
    },

    # ── Method limits ──────────────────────────────
    {
        "label": tr("billing_feature_methods_weekly"),
        "icon": "📚",
        "render": lambda plan: render_limit(
            plan.get("weekly_method_quota")
        ),
    },
    {
        "label": tr("billing_feature_methods_total"),
        "icon": "📚",
        "render": lambda plan: render_limit(
            plan.get("total_method_quota")
        ),
    },
]

# ==================================================
# PLAN COMPARISON UI
# ==================================================
selected_interval = st.session_state.selected_interval

st.subheader(tr("billing_choose_plan"))

# Header row (plan names)
header_cols = st.columns(len(plans) + 1)

with header_cols[0]:
    st.markdown(
        "<div style='min-height:3.2rem'></div>",
        unsafe_allow_html=True,
    )

for col, plan in zip(header_cols[1:], plans):
    with col:
        st.markdown(
            f"""
            <div style="
                min-height:3.2rem;
                display:flex;
                align-items:center;
                justify-content:center;
            ">
                <strong style="font-size:1.1rem">
                    {plan['name'].capitalize()}
                </strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Feature rows
for row in FEATURE_ROWS:
    row_cols = st.columns(len(plans) + 1)

    # Feature label
    with row_cols[0]:
        st.markdown(
            f"""
            <div style="
                min-height:2.6rem;
                display:flex;
                align-items:center;
            ">
                <strong>{row['icon']} {row['label']}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Feature values
    for col, plan in zip(row_cols[1:], plans):
        with col:
            st.markdown(
                f"""
                <div style="
                    min-height:2.6rem;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                ">
                    {row['render'](plan)}
                </div>
                """,
                unsafe_allow_html=True,
            )

# Button cols

button_cols = st.columns(len(plans) + 1)

with button_cols[0]:
    st.markdown("")

if st.session_state.user:
    for col, plan in zip(button_cols[1:], plans):
        with col:
            if st.button(
                tr("billing_select_plan").format(label=plan["name"]),
                key=f"select_{plan['name']}",
                use_container_width=True,
            ):
                st.session_state.selected_interval = plan["name"]
else:
    st.error(
        "🔐 **" + tr("billing_login_required_title") + "**\n\n"
        + tr("billing_login_required_text")
    )

# --------------------------------------------------
# Require selection
# --------------------------------------------------
if not selected_interval and st.session_state.user:
    st.info(tr("billing_select_prompt"))
    st.stop()

st.divider()

# --------------------------------------------------
# Conditions
# --------------------------------------------------
st.markdown("### ℹ️ " + tr("billing_conditions_title"))
st.markdown(tr("billing_conditions_text"))

# --------------------------------------------------
# Checkout
# --------------------------------------------------
if st.session_state.user:
    if st.button(tr("billing_checkout"), use_container_width=True):
        with st.spinner(tr("billing_redirecting")):
            res = requests.post(
                f"{st.secrets['supabase']['functions_url']}/create-checkout",
                json={
                    "interval": selected_interval,
                    "user_id": st.session_state.user.id,
                    "email": st.session_state.user.email,
                },
                headers={
                    "Authorization": f"Bearer {st.session_state.session.access_token}"
                },
                timeout=15,
            )

        #if res.status_code != 200:
        #    st.error(tr("billing_checkout_failed"))
        #    st.stop()

        if res.status_code != 200:
            st.error("Failed to create checkout session.")
            st.write("Status code:", res.status_code)
            st.write("Response text:", res.text)
            st.stop()

        checkout_url = res.json()["url"]
        st.markdown(f"👉 [{tr('billing_proceed_payment')}]({checkout_url})")

if st.session_state.user and profile.get("stripe_customer_id"):
    if st.button("🧾 Manage subscription"):
        res = requests.post(
            f"{st.secrets['supabase']['functions_url']}/create-portal-session",
            json={
                "customer_id": profile["stripe_customer_id"]
            },
            headers={
                "Authorization": f"Bearer {st.session_state.session.access_token}"
            },
            timeout=15,
        )

        if res.status_code != 200:
            st.error("Failed to open billing portal.")
        else:
            portal_url = res.json()["url"]
            st.markdown(f"👉 [Open billing portal]({portal_url})")
