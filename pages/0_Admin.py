# pages/1_Admin.py
import streamlit as st
from utils.db import get_user, set_paid

st.set_page_config(page_title="Admin", page_icon="🔧")
st.title("🔧 Admin Panel")

username = st.text_input("Enter username to toggle paid flag:")
if st.button("Toggle paid"):
    user = get_user(username)
    if not user:
        st.error("User not found.")
    else:
        current_paid = bool(user[2])
        set_paid(username, not current_paid)
        st.success(f"User '{username}' set to {'paid ✅' if not current_paid else 'unpaid ❌'}.")
