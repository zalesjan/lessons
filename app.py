# app.py
import streamlit as st
from datetime import date

from openai import OpenAI

# --------------------------------------------------
# Static teaching methods
# --------------------------------------------------
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

 #---- If st.switch_page is not available in your version:
 #st.markdown(f"[{t['open_method']}: {v['center_label']}](/1_Methods?method={v['center_target_id']})")
 #or:
 #st.experimental_set_query_params(method=v["center_target_id"])
 #st.experimental_rerun()

# --------------------------------------------------
# Setup
# --------------------------------------------------
from supabase import create_client, Client
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(url, key)
client = OpenAI()  # Requires OPENAI_API_KEY env var
MODEL = "gpt-4o-mini"

st.set_page_config(page_title="Lesson Generator", page_icon="🎓", layout="centered")

# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    # create profile if not exists
    supabase.table("profiles").insert({"id": user_id}).execute()
    return {"paid": False, "free_generations_used": 0, "last_generation_date": None}

def update_profile(user_id, data: dict):
    supabase.table("profiles").update(data).eq("id", user_id).execute()

# --------------------------------------------------
# Authentication UI
# --------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🎓 AI Lesson Generator")
    mode = st.radio("Choose mode:", ["Login", "Sign up"], horizontal=True)
    email = st.text_input("Email address")
    pw = st.text_input("Password", type="password")

    if mode == "Sign up":
        if st.button("Create Account"):
            try:
                auth_res = supabase.auth.sign_up({"email": email, "password": pw})
                if auth_res.user:
                    st.success("✅ Check your email to confirm registration.")
                else:
                    st.error("Could not sign up.")
            except Exception as e:
                st.error(str(e))
    else:  # Login
        if st.button("Login"):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                if auth_res.user:
                    st.session_state.user = auth_res.user
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials.")
            except Exception as e:
                st.error(str(e))
    st.stop()

# --------------------------------------------------
# Logged-in area
# --------------------------------------------------
user = st.session_state.user
profile = get_profile(user.id)
st.success(f"Welcome {user.email}!")

st.sidebar.button("Logout", on_click=lambda: st.session_state.pop("user"))

paid = profile.get("paid", False)
used = profile.get("free_generations_used", 0)
last = profile.get("last_generation_date")

today = str(date.today())
can_generate = False

if paid:
    st.info("💎 Premium access: unlimited generations.")
    can_generate = True
else:
    remaining = 7 - used
    st.warning(f"🆓 Free tier: {remaining} generations left (1 per day).")
    if used >= 7:
        st.error("No more free generations available.")
    elif last == today:
        st.error("Already generated today.")
    else:
        can_generate = True

# Manual “Pay” unlock
if not paid and st.button("💳 Mark as Paid (Manual)"):
    update_profile(user.id, {"paid": True})
    st.experimental_rerun()

st.markdown("---")


# --------------------------------------------------
# AI generation
# --------------------------------------------------
st.subheader("✨ Generate AI-Adapted Lesson")
topic = st.text_input("Enter your lesson topic:")

if st.button("Generate Lesson"):
    if not topic:
        st.warning("Enter a topic first.")
    elif not can_generate:
        st.error("You can’t generate right now.")
    else:
        with st.spinner("Generating lesson..."):
            prompt = f"""
            You are an expert instructional designer.
            Using the Jigsaw, Bus Stops, and Line methods,
            create concise lesson outlines for the topic "{topic}".
            Each method: title, objective, 1–2 before activities,
            1 central activity, and 1–2 after activities.
            Keep total under 250 words.
            """
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=350,
                )
                st.markdown(resp.choices[0].message.content)

                # Update usage
                if not paid:
                    update_profile(user.id, {
                        "free_generations_used": used + 1,
                        "last_generation_date": today
                    })
            except Exception as e:
                st.error(f"API error: {e}")
