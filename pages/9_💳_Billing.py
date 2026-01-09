import streamlit as st
import requests
from modules.languages import translations
from modules.supabase_client import get_guest_client

if "selected_interval" not in st.session_state:
    st.session_state.selected_interval = None

st.set_page_config(page_title="Billing", page_icon="💳")

# --------------------------------------------------
# Language (reuse app.py state)
# --------------------------------------------------
lang = st.session_state.get("lang", "en")
t = translations.get(lang, translations["en"])

def tr(key: str) -> str:
    return translations[lang].get(key, key)

# --------------------------------------------------
# Page header
# --------------------------------------------------
#st.title(tr("billing_title"))
#st.markdown(tr("billing_intro"))
st.title("💳 Upgrade to Didact.io Pro plan")
st.badge(
    """
    Upgrade your **Didact.io** account to unlock deeper access to effective
    teaching methods and and higher usage limits on AI-assisted lesson preparation.
    """
)

# --------------------------------------------------
# Safety checks
# --------------------------------------------------
if not st.session_state.user:

    st.info(
        "🔐 **Login required**\n\n"
        "To subscribe to **Didact.io Pro**, please sign in or create a free account first."
    )

    if st.button("👉 Sign in or create account"):
        st.query_params.update({
        "action": "login",
        "next": "billing"
        })

        st.session_state.force_login = True
        st.switch_page("app.py")

        st.stop()

if "supabase" not in st.session_state:
    st.error("Supabase client not initialized.")
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
    #st.error(tr("billing_no_plans"))
    st.stop()


# --------------------------------------------------
# Plan selection UI
# --------------------------------------------------
st.subheader(tr("billing_choose_plan"))

cols = st.columns(len(plans))
selected_interval = st.session_state.selected_interval

for col, plan in zip(cols, plans):
    with col:
        if plan.get("is_recommended"):
            st.markdown("⭐ **" + tr("billing_recommended") + "**")
        if plan.get("name") != "none":
            st.markdown(f"### {plan['name']}")
            st.markdown(f"**{plan['price']}**")

            if plan.get("daily_lesson_quota"):
                st.markdown(
                    tr("billing_ai_limit").format(
                        ai_generations=plan["daily_lesson_quota"]
                    )
                )
            else:
                st.markdown(tr("billing_ai_unlimited"))

            if st.button(
                tr("billing_select_plan").format(label=plan["name"]),
                key=f"select_{plan['name']}",
            ):
                st.session_state.selected_interval = plan["name"]


# --------------------------------------------------
# Require selection
# --------------------------------------------------
if not selected_interval:
    st.info(tr("billing_select_prompt"))
    st.stop()

st.divider()

# --------------------------------------------------
# Conditions
# --------------------------------------------------
#st.markdown(tr("billing_conditions"))
st.markdown(
    """
    ### ℹ️ Subscription conditions

    - Cancel anytime via the billing portal
    - Secure payment handled by **Stripe**
    - We never see or store your payment details
    - VAT and invoices handled automatically by Stripe
    """
)

# --------------------------------------------------
# Checkout
# --------------------------------------------------
if st.button(tr("billing_checkout")):
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