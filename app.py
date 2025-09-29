# app.py
import streamlit as st
from utils.data import methods

st.set_page_config(page_title="Lessons", page_icon="📚", layout="centered")

# --- language toggle in sidebar ---
if "lang" not in st.session_state:
    st.session_state.lang = "en"
lang = st.sidebar.selectbox("Language / Jazyk", ["en", "cs"], index=0 if st.session_state.lang=="en" else 1)
st.session_state.lang = lang

t = {
    "en": {
        "title": "Composed Lesson Variants",
        "subtitle": "Each variant centers a different method and includes 1–2 lead-in and 1–2 consolidation steps.",
        "before": "Before",
        "center": "Center",
        "after": "After",
        "subject": "Subject",
        "level": "Level",
        "objective": "Objective",
        "open_method": "Open method manual",
    },
    "cs": {
        "title": "Varianty složené lekce",
        "subtitle": "Každá varianta staví na jiné metodě a obsahuje 1–2 úvodní a 1–2 závěrečné aktivity.",
        "before": "Před",
        "center": "Střed",
        "after": "Po",
        "subject": "Předmět",
        "level": "Úroveň",
        "objective": "Cíl",
        "open_method": "Otevřít metodiku",
    },
}[lang]

# --- three lesson variants (center -> method id) ---
variants = [
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

st.title(t["title"])
st.caption(t["subtitle"])

for v in variants:
    with st.container(border=True):
        st.subheader(v["title"])
        st.write(f"**{t['subject']}:** {v['subject']} · **{t['level']}:** {v['level']} · **{t['objective']}:** {v['objective']}")

        # Before
        if v["before"]:
            st.markdown(f"##### {t['before']}")
            cols = st.columns(len(v["before"]))
            for col, (name, summary, mins) in zip(cols, v["before"]):
                with col:
                    st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")

        # Center — include a button that navigates to Methods with a query param
        st.markdown(f"##### {t['center']} — {v['center_label']}")  # label + center method name
        name, summary, mins = v["center"]
        st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")
        go = st.button(f"▶ {t['open_method']}: {v['center_label']}", key=v["id"])
        if go:
            st.query_params["method"] = v["center_target_id"]
            st.switch_page("pages/1_Methods.py")  # Streamlit 1.22+; if not available, see alt below

        # After
        if v["after"]:
            st.markdown(f"##### {t['after']}")
            cols = st.columns(len(v["after"]))
            for col, (name, summary, mins) in zip(cols, v["after"]):
                with col:
                    st.write(f"**{name}**  \n{summary}  \n*⏱ {mins} min*")

# ---- If st.switch_page is not available in your version:
# st.markdown(f"[{t['open_method']}: {v['center_label']}](/1_Methods?method={v['center_target_id']})")
# or:
# st.experimental_set_query_params(method=v["center_target_id"])
# st.experimental_rerun()
