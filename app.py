import streamlit as st
from modules.methods_manipulation import select_suitable_methods
from modules.db_operations import get_db_connection, generate_lesson_plan


# Define subject categories
subject_categories = {
    "Humanities": [
        "Art", "History", "Music", "Performing Arts", "Communication", 
        "Social Studies", "Philosophy", "Language"
    ],
    "Natural Sciences": [
        "Science", "Math", "Health", "Geography"
    ],
    "Others": [
        "Logic"
    ]
}

# All available subjects
all_subjects = [
    "Art", "Logic", "History", "Music", "Performing Arts", "Communication",
    "Social Studies", "Math", "Health", "Geography", "Philosophy", 
    "Science", "Language"
]


# Streamlit App Title
#st.title("Lesson Plan Generator")

# Section: Lesson Plan Generation
st.header("Lesson Plan Generation")

# Form to input lesson plan filter criteria
with st.form(key='new_generate_lesson_form'):
    min_age = st.number_input("Minimum Age", min_value=1, max_value=18, value=3)
    max_age = st.number_input("Maximum Age", min_value=1, max_value=18, value=8)

    # Option to either select a category or a specific subject
    selected_category = st.selectbox("Select Category", ["None"] + list(subject_categories.keys()))
    selected_subject = st.selectbox("Or Select Subject", ["None"] + all_subjects)
    total_max_duration = st.number_input("Maximum total duration", min_value=1, max_value=1000, value=90)

    # New: Define block time allocation (percentage for each block)
    block_allocations = {}
    for i in range(1, 6):  # Assuming blocks 1 to 5
        block_allocations[i] = st.slider(f"Block {i} time allocation (in percentage)", min_value=0, max_value=100, value=0, step=5)
    
    new_generate_lesson_button = st.form_submit_button(label="Generate Lesson Plan")

if new_generate_lesson_button:
# Ensure the total percentage is 100%
    if sum(block_allocations.values()) != 100:
        st.error("The total block time allocation must sum to 100%!")
    else:
        # Calculate the max duration for each block based on user input
        block_durations = {block: (block_allocations[block] / 100) * total_max_duration for block in block_allocations}

    
        # Collect filter values
        filters = {
            'category': selected_category if selected_category != "None" else None,
            'subject': selected_subject if selected_subject != "None" else None,
            'min_age': min_age,
            'max_age': max_age,
            'total_max_duration': total_max_duration,
            'block_durations': block_durations  # Pass block durations
        }

    # Call the lesson plan generation function
    methods = generate_lesson_plan(filters, subject_categories)
    #st.write(f"Methods retrieved: {methods}")  # Debugging

    if methods:
        suitable_methods = select_suitable_methods(methods, total_max_duration, block_allocations)

        if suitable_methods:
            st.subheader("Generated Lesson Plan")
            for method in suitable_methods:
                st.write(f"**Method ID**: {method[0]}")
                st.write(f"**Name**: {method[1]}")
                st.write(f"**Description**: {method[2]}")
                st.write(f"**Duration**: {method[3]} minutes")
                st.write(f"**Age Group**: {method[4]}")
                st.write(f"**Block**: {method[5]}")
                st.write(f"**Subject**: {method[6]}")
                st.write(f"**Topic**: {method[7]}")
                st.write(f"**Tools**: {method[8]}")
                st.write(f"**Sources**: {method[9]}")
                st.write("---")
        else:
            st.write("No suitable methods found.")
    else:
        st.write("No methods found for the selected filters.")

# Section: Define Lesson
st.header("Define and Save Lesson Plan")

# Save lesson plan form
with st.form(key='save_lesson_form'):
    user_id = st.number_input("User ID", value=1)
    filters_description = st.text_input("Filters Description")
    filters_subject = st.selectbox(
        "Select Subject", 
        [
            "Art", "Logic", "History", "Music", "Performing Arts", "Communication", 
            "Social Studies", "Math", "Health", "Geography", "Philosophy", "Science", "Language"
        ]
    )
    filters_topic = st.text_input("Filters Topic")
    save_lesson_button = st.form_submit_button(label="Save Lesson Plan")

if save_lesson_button:
    if user_id and filters_description:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Insert lesson and retrieve ID
                cursor.execute(
                    "INSERT INTO Lessons (user_id, topic) VALUES (%s, %s) RETURNING lesson_id", 
                    (user_id, filters_topic)
                )
                lesson_id = cursor.fetchone()[0]

                # Save selected lesson methods
                for order, method in enumerate(suitable_methods):  # Uses suitable methods from generated lesson plan
                    cursor.execute(
                        "INSERT INTO LessonMethods (lesson_id, method_id, sequence_order) VALUES (%s, %s, %s)",
                        (lesson_id, method[0], order)
                    )

                conn.commit()
                st.success(f"Lesson Plan saved with ID {lesson_id}")

        except Exception as e:
            st.error(f"Failed to save lesson plan: {str(e)}")
    else:
        st.error("User ID and filters description are required to save the lesson plan.")
