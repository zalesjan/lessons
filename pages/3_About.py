import streamlit as st
from modules.languages import translations

st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")

# -------------------------------------------------------------------
# LANGUAGE SELECTION WITH FLAGS
# -------------------------------------------------------------------

LANG_OPTIONS = {
    "en": "🇬🇧 English",
    "cs": "🇨🇿 Čeština",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
}

if "lang" not in st.session_state:
    st.session_state.lang = "en"

# Preselect the correct label for the current language
current_language_label = LANG_OPTIONS[st.session_state.lang]

selected_label = st.sidebar.selectbox(
    "🌐 Language / Jazyk / Langue / Idioma / Sprache",
    list(LANG_OPTIONS.values()),
    index=list(LANG_OPTIONS.values()).index(current_language_label)
)

# reverse-lookup language code by label
lang = [code for code, label in LANG_OPTIONS.items() if label == selected_label][0]
st.session_state.lang = lang

t = translations[lang]  # currently selected tanslations


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
    st.markdown(t["about_short"])

elif page == "📘 About (Full)":
    st.markdown(t["about_full"])

elif page == "🛠️ Guide":
    st.markdown(t["guide"])

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