## app.py
#import streamlit as st
#from utils.data import methods
#
#st.set_page_config(page_title="Lessons", page_icon="📚", layout="centered")
#
## --- language toggle in sidebar ---
#if "lang" not in st.session_state:
#    st.session_state.lang = "en"
#lang = st.sidebar.selectbox("Language / Jazyk", ["en", "cs"], index=0 if st.session_state.lang=="en" else 1)
#st.session_state.lang = lang
#
#t = {
#    "en": {
#        "title": "Composed Lesson Variants",
#        "subtitle": "Each variant centers a different method and includes 1–2 lead-in and 1–2 consolidation steps.",
#        "before": "Before",
#        "center": "Center",
#        "after": "After",
#        "subject": "Subject",
#        "level": "Level",
#        "objective": "Objective",
#        "open_method": "Open method manual",
#    },
#    "cs": {
#        "title": "Varianty složené lekce",
#        "subtitle": "Každá varianta staví na jiné metodě a obsahuje 1–2 úvodní a 1–2 závěrečné aktivity.",
#        "before": "Před",
#        "center": "Střed",
#        "after": "Po",
#        "subject": "Předmět",
#        "level": "Úroveň",
#        "objective": "Cíl",
#        "open_method": "Otevřít metodiku",
#    },
#}[lang]
#
## --- three lesson variants (center -> method id) ---
#variants = [
#    {
#        "id": "lesson-jigsaw",
#        "title": "Ecosystems & Energy Flow",
#        "objective": "Students build expertise on trophic levels and teach peers.",
#        "subject": "Science",
#        "level": "Grade 8–9",
#        "center_label": "Jigsaw",
#        "center_target_id": "jigsaw",
#        "before": [
#            ("Advance Organizer", "Preview today’s concept map: producers → consumers → decomposers.", 5),
#            ("Think–Pair–Share", "Activate prior knowledge about local food chains.", 5),
#        ],
#        "center": ("Jigsaw", "Expert groups master subtopics, then teach in mixed groups.", 25),
#        "after": [
#            ("Whole-class Synthesis", "Report key takeaways; resolve misconceptions.", 5),
#            ("Exit Ticket", "One energy transfer example + one open question.", 5),
#        ],
#    },
#    {
#        "id": "lesson-bus",
#        "title": "Causes of the Industrial Revolution",
#        "objective": "Generate and refine ideas about social, tech, and economic drivers.",
#        "subject": "History",
#        "level": "Grade 9–10",
#        "center_label": "Bus Stops",
#        "center_target_id": "bus-stops",
#        "before": [
#            ("Quickwrite", "What made the Industrial Revolution possible?", 4),
#            ("Prompt Unpack", "Clarify prompts: resources, inventions, labor, capital, policy.", 3),
#        ],
#        "center": ("Bus Stops", "Rotate stations, add ideas, build on prior notes.", 20),
#        "after": [
#            ("Gallery Debrief", "Identify strongest evidence or surprises.", 6),
#            ("3-2-1", "3 insights, 2 questions, 1 modern connection.", 4),
#        ],
#    },
#    {
#        "id": "lesson-line",
#        "title": "Ethics of AI in the Classroom",
#        "objective": "Articulate positions and engage with counter-arguments.",
#        "subject": "Civics / ICT",
#        "level": "Grade 10–11",
#        "center_label": "Line (Human Continuum)",
#        "center_target_id": "line",
#        "before": [
#            ("Anticipation Guide", "Agree/disagree statements (e.g., “AI makes cheating inevitable”).", 5),
#            ("Evidence Snapshots", "Pairs skim short excerpts on AI benefits/risks.", 5),
#        ],
#        "center": ("Line Method (Human Continuum)", "Stand along agree↔disagree; explain; move with evidence.", 18),
#        "after": [
#            ("Counter-claim Pairs", "Formulate a counter-argument.", 6),
#            ("Reflect & Commit", "Has your position shifted? Why/why not?", 4),
#        ],
#    },
#]
#
#st.title(t["title"])
#st.caption(t["subtitle"])
#
#for v in variants:
#    with st.container(border=True):
#        st.subheader(v["title"])
#        st.write(f"**{t['subject']}:** {v['subject']} · **{t['level']}:** {v['level']} · **{t['objective']}:** {v['objective']}")
#
#        # Before
#        if v["before"]:
#            st.markdown(f"##### {t['before']}")
#            cols = st.columns(len(v["before"]))
#            for col, (name, summary, mins) in zip(cols, v["before"]):
#                with col:
#                    st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")
#
#        # Center — include a button that navigates to Methods with a query param
#        st.markdown(f"##### {t['center']} — {v['center_label']}")  # label + center method name
#        name, summary, mins = v["center"]
#        st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")
#        go = st.button(f"▶ {t['open_method']}: {v['center_label']}", key=v["id"])
#        if go:
#            st.query_params["method"] = v["center_target_id"]
#            st.switch_page("pages/1_Methods.py")  # Streamlit 1.22+; if not available, see alt below
#
#        # After
#        if v["after"]:
#            st.markdown(f"##### {t['after']}")
#            cols = st.columns(len(v["after"]))
#            for col, (name, summary, mins) in zip(cols, v["after"]):
#                with col:
#                    st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")
#
# ---- If st.switch_page is not available in your version:
# st.markdown(f"[{t['open_method']}: {v['center_label']}](/1_Methods?method={v['center_target_id']})")
# or:
# st.experimental_set_query_params(method=v["center_target_id"])
# st.experimental_rerun()
#---------------------------------------------------------------------
#---------------------------------------------------------------------
# before was an old, semi/static app page, bellow is the AI-driven one
#---------------------------------------------------------------------
#---------------------------------------------------------------------
# app.py
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Lessons", page_icon="📚", layout="centered")
client = OpenAI()

# -------------------------------
# ORIGINAL lesson variants template
# -------------------------------
base_variants = [
    {
        "id": "lesson-jigsaw",
        "title": "Ecosystems & Energy Flow",
        "objective": "Students build expertise on trophic levels and teach peers.",
        "subject": "Science",
        "level": "Grade 8–9",
        "center_label": "Jigsaw",
        "center_target_id": "jigsaw",
        "before": [
            ("Advance Organizer", "Preview today’s concept map: producers → consumers → decomposers.", 5),
            ("Think–Pair–Share", "Activate prior knowledge about local food chains.", 5),
        ],
        "center": ("Jigsaw", "Expert groups master subtopics, then teach in mixed groups.", 25),
        "after": [
            ("Whole-class Synthesis", "Report key takeaways; resolve misconceptions.", 5),
            ("Exit Ticket", "One energy transfer example + one open question.", 5),
        ],
    },
    {
        "id": "lesson-bus",
        "title": "Causes of the Industrial Revolution",
        "objective": "Generate and refine ideas about social, tech, and economic drivers.",
        "subject": "History",
        "level": "Grade 9–10",
        "center_label": "Bus Stops",
        "center_target_id": "bus-stops",
        "before": [
            ("Quickwrite", "What made the Industrial Revolution possible?", 4),
            ("Prompt Unpack", "Clarify prompts: resources, inventions, labor, capital, policy.", 3),
        ],
        "center": ("Bus Stops", "Rotate stations, add ideas, build on prior notes.", 20),
        "after": [
            ("Gallery Debrief", "Identify strongest evidence or surprises.", 6),
            ("3-2-1", "3 insights, 2 questions, 1 modern connection.", 4),
        ],
    },
    {
        "id": "lesson-line",
        "title": "Ethics of AI in the Classroom",
        "objective": "Articulate positions and engage with counter-arguments.",
        "subject": "Civics / ICT",
        "level": "Grade 10–11",
        "center_label": "Line (Human Continuum)",
        "center_target_id": "line",
        "before": [
            ("Anticipation Guide", "Agree/disagree statements (e.g., “AI makes cheating inevitable”).", 5),
            ("Evidence Snapshots", "Pairs skim short excerpts on AI benefits/risks.", 5),
        ],
        "center": ("Line Method (Human Continuum)", "Stand along agree↔disagree; explain; move with evidence.", 18),
        "after": [
            ("Counter-claim Pairs", "Formulate a counter-argument.", 6),
            ("Reflect & Commit", "Has your position shifted? Why/why not?", 4),
        ],
    },
]

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("🧭 Lesson Blueprints")
st.caption("Each variant centers a different method (Jigsaw, Bus Stops, Line) — AI can adapt them to your topic.")

topic = st.text_input("🎯 Enter your lesson topic (e.g., *Climate Change*, *Fractions*, *Shakespearean Drama*):")

if st.button("✨ Adapt Lessons with AI") and topic:
    st.session_state.topic = topic
    st.session_state.variants = []
    with st.spinner("AI is adapting lesson plans..."):
        for variant in base_variants:
            prompt = f"""
You are an expert instructional designer.
Take this lesson plan structure and rewrite it for a lesson on the topic "{topic}".
Keep the same structure (title, objective, subject, level, center_label, before/center/after activities),
but make the content pedagogically meaningful and realistic for the topic.
Return the result as readable text, not JSON.
Here is the base variant:
{variant}
"""
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a pedagogy assistant creating lesson plans."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
            )
            st.session_state.variants.append(resp.choices[0].message.content)

# -------------------------------
# Display
# -------------------------------
variants = st.session_state.get("variants", base_variants)
topic_label = st.session_state.get("topic", None)
if topic_label:
    st.subheader(f"🪄 Adapted for topic: *{topic_label}*")

for v in variants:
    st.markdown("----")
    if isinstance(v, str):
        # LLM returned readable text
        st.markdown(v)
    else:
        # fallback to default static version
        st.subheader(v["title"])
        st.write(f"**Objective:** {v['objective']}")
        st.write(f"**Subject:** {v['subject']} · **Level:** {v['level']}")
        st.markdown(f"**Center method:** {v['center_label']}")
        st.markdown("**Before:**")
        for name, desc, mins in v["before"]:
            st.markdown(f"- **{name}** ({mins} min): {desc}")
        st.markdown("**Center:**")
        c_name, c_desc, c_min = v["center"]
        st.markdown(f"- **{c_name}** ({c_min} min): {c_desc}")
        st.markdown("**After:**")
        for name, desc, mins in v["after"]:
            st.markdown(f"- **{name}** ({mins} min): {desc}")
#---------------------------------------------------------------------
#---------------------------------------------------------------------
# before was an old AI-driven page, below is one with paywall
#---------------------------------------------------------------------
#---------------------------------------------------------------------
# app.py
import streamlit as st
from openai import OpenAI
from datetime import date
from utils.db import init_db, add_user, get_user, record_generation

init_db()
st.set_page_config(page_title="Lesson Generator", page_icon="🎓", layout="centered")

# OpenAI setup — use cheaper model
client = OpenAI()
MODEL = "gpt-4o-mini"   # low-cost, fast

# -----------------------------
# Authentication
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🎓 AI Lesson Generator")

if not st.session_state.user:
    tabs = st.tabs(["🔑 Login", "🆕 Sign Up"])
    with tabs[0]:
        email = st.text_input("Email address")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            record = get_user(email)
            if record and record[1] == pw:
                st.session_state.user = {
                    "username": record[0],
                    "paid": bool(record[2]),
                    "used": record[3],
                    "last_date": record[4],
                }
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    with tabs[1]:
        email = st.text_input("Email address")
        new_user = st.text_input("Choose username (Optional)")
        new_pw = st.text_input("Choose password", type="password")
        if st.button("Create Account"):
            if not email or "@" not in email:
                st.error("Please enter a valid email.")
            else:
                try:
                    add_user(email=email, username=new_user, password=new_pw)
                    st.success("Account created! Please check your email to verify (mock).")
                except Exception as e:
                    st.error(f"Could not create user: {e}")
    st.stop()

# -----------------------------
# After login
# -----------------------------
user = st.session_state.user
st.success(f"Welcome, {user['username']}!")

username = user["username"]
paid = user["paid"]
used = user["used"] or 0
last = user["last_date"]

# ------------- Free tier check -------------
today = str(date.today())
can_generate = False

if paid:
    st.info("💎 You have premium access — unlimited generations.")
    can_generate = True
else:
    st.warning(f"🆓 Free tier: {7 - used} generations left (1 per day).")
    if used >= 7:
        st.error("You've reached your 7 total free generations limit.")
    elif last == today:
        st.error("You already generated a lesson today. Come back tomorrow!")
    else:
        can_generate = True
        st.caption("You can use AI once today to adapt your lesson.")

# -----------------------------
# Static methods section (always visible)
# -----------------------------
st.markdown("---")
st.subheader("📘 Teaching Methods Overview")
st.markdown("""
- **Jigsaw** — Students become experts on one subtopic, then teach peers.  
- **Bus Stops** — Groups rotate between stations, adding and refining ideas.  
- **Line (Human Continuum)** — Students take a position on an issue and justify it.  
""")

# -----------------------------
# AI Lesson adaptation section
# -----------------------------
st.markdown("---")
st.subheader("✨ Generate AI-Adapted Lesson")

topic = st.text_input("Enter your lesson topic:")

if st.button("Generate Lesson"):
    if not topic:
        st.warning("Please enter a topic first.")
    elif not can_generate:
        st.error("You cannot generate today.")
    else:
        with st.spinner("Generating lesson..."):
            prompt = f"""
            You are an expert instructional designer.
            Using the Jigsaw, Bus Stops, and Line (Human Continuum) methods,
            create concise lesson outlines for the topic "{topic}".
            Each method should include: 
            - Title
            - Objective
            - 1–2 before activities
            - 1 central activity (the method)
            - 1–2 after activities
            Write clearly and keep total length short (around 250 words).
            """
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=350,  # shorter = cheaper
                )
                st.markdown(resp.choices[0].message.content)
                if not paid:
                    record_generation(username)
            except Exception as e:
                st.error(f"API error: {e}")
