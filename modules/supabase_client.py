from supabase import create_client, ClientOptions
import streamlit as st

def get_guest_client():
    """
    Supabase client for unauthenticated users.
    Uses anon key + x-anon-id for RLS.
    """
    anon_id = st.session_state.get("anon_id")
    if not anon_id:
        raise RuntimeError("anon_id missing: must be initialized in app.py")

    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],  # anon key
        options=ClientOptions(
            headers={"x-anon-id": anon_id}
        )
    )

def get_user_client(session):
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
        options=ClientOptions(
            headers={
                "Authorization": f"Bearer {session.access_token}"
            }
        )
    )
