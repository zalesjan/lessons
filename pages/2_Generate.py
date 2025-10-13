# pages/2_Generate.py
import streamlit as st

st.set_page_config(page_title="Generate", page_icon="⚙️", layout="centered")
st.title("Generate a lesson")

topic = st.text_input("Topic")
level = st.text_input("Level")
method = st.text_input("Method (e.g., Jigsaw)")
language = st.selectbox("Language", ["en", "cs"], index=0)
length = st.number_input("Length (min)", min_value=5, max_value=180, value=45)

if st.button("Generate"):
    st.success(f"Generated lesson for '{topic}' · {level} · method {method} · {language} · {length} min")
