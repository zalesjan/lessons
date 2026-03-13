from supabase import create_client, ClientOptions
import streamlit as st
import uuid

def get_guest_client():
    """
    Supabase client for unauthenticated users.
    Uses anon key + x-anon-id for RLS.
    """
    anon_id = get_or_create_anon_id()

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