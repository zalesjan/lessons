import streamlit as st
from modules.languages import translations

LANG_OPTIONS = {
    "en": "🇬🇧 English",
    "cs": "🇨🇿 Čeština",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
}


class LanguageManager:
    """Centralized language controller for the entire Streamlit app."""

    @staticmethod
    def init_language(profile_language=None):
        """
        Ensures language is initialized based on priority:
        1. URL ?lang=xx
        2. profile preferred language (from Supabase)
        3. session_state.lang
        4. fallback: English
        """

        # 1. URL priority
        query_lang = st.query_params.get("lang")
        if isinstance(query_lang, list):  
            query_lang = query_lang[0]

        if query_lang in LANG_OPTIONS:
            st.session_state.lang = query_lang

        # 2. Profile preferred language (only if not overridden by URL)
        elif profile_language and profile_language in LANG_OPTIONS:
            if "lang" not in st.session_state:
                st.session_state.lang = profile_language

        # 3. Already set in session_state
        elif "lang" in st.session_state:
            pass

        # 4. Fallback
        else:
            st.session_state.lang = "cs"

        return st.session_state.lang

    @staticmethod
    def sidebar_selector():
        """Sidebar selector with flags. Writes result into session_state."""
        current = st.session_state.lang
        current_label = LANG_OPTIONS[current]

        selected_label = st.sidebar.selectbox(
            "🌐 Language / Jazyk / Langue / Idioma / Sprache",
            list(LANG_OPTIONS.values()),
            index=list(LANG_OPTIONS.values()).index(current_label)
        )

        # Reverse lookup
        new_lang = next(k for k, v in LANG_OPTIONS.items() if v == selected_label)
        st.session_state.lang = new_lang
        st.query_params.update({"lang": new_lang})  # store in URL for persistence

        return new_lang

    @staticmethod
    def t():
        """Returns translations for the active language. With fallback."""
        lang = st.session_state.get("lang", "cs")
        return translations.get(lang, translations["cs"])

    @staticmethod
    def tr(key):
        """Returns translation for a specific key with fallback warning."""
        lang = st.session_state.get("lang", "tr")
        return translations.get(lang, {}).get(key, f"⚠️ Missing translation: {key}")
