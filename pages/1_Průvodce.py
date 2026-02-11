import streamlit as st
from modules.languages import translations
from modules.language_manager import LanguageManager

st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")

# -------------------------------------------------------------------
# LANGUAGE SELECTION WITH FLAGS
# -------------------------------------------------------------------

tr = LanguageManager.tr      # load translations
LanguageManager.sidebar_selector()  # optional: show language menu

# -------------------------------------------------------------------
# PAGE SELECTION
# -------------------------------------------------------------------
page = st.sidebar.radio(
    "📄 About Menu",
    ["🔹 About (Short)", "📘 About (Full)", "🛠️ Guide"]
)

# -------------------------------------------------------------------
# PAGE ROUTER
# -------------------------------------------------------------------
if page == "🔹 About (Short)":
    st.markdown(tr("about_short"))

elif page == "📘 About (Full)":
    st.markdown(tr("about_full"))

elif page == "🛠️ Guide":
    st.markdown(tr("guide"))

# ==================================================
# ABOUT SECTION
# ==================================================
#def toggle_about(mode):
#    st.session_state.about_mode = (
#        None if st.session_state.about_mode == mode else mode
#    )
#    
#cols = st.columns(2)
#
#with cols[0]:
#    if st.button(t["about_short_btn"]):
#        toggle_about("short")
#
#with cols[1]:
#    if st.button(t["about_full_btn"]):
#        toggle_about("full")
#
#if st.session_state.about_mode == "short":
#    st.info(t["about_short"])
#
#elif st.session_state.about_mode == "full":
#    st.info(t["about_full"])