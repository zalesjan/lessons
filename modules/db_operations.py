from contextlib import contextmanager
import psycopg2

# PostgreSQL database connection details
DB_HOST = '147.251.253.245'
DB_PORT = '5432'
DB_NAME = 'EuFoRIa_trees_db'
DB_USER = 'vukoz'
DB_PASSWORD = 'W0Ja3l9WbabOxWatduegk6akPTJg9kZi6JxaKuWIjncX7AK0ct2vYaL9kDExoVjH'

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        yield conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
    finally:
        if conn:
            conn.close()

def generate_lesson_plan(filters, subject_categories):
    subject = filters.get('subject')
    category = filters.get('category')
    min_age = filters.get('min_age')
    max_age = filters.get('max_age')
    max_duration = filters.get('max_duration')

    # Build subject list based on category if no subject is directly selected
    if category and not subject:
        subjects = subject_categories.get(category, [])
    else:
        subjects = [subject] if subject else []

    # Build the query with dynamic filters
    query = """
    SELECT method_id, method_name, description, duration, age_group, block, subject, topic, tools, sources 
    FROM test_db.DidacticMethods 
    WHERE 1=1"""
    params = []

    if subjects:
        query += " AND subject IN %s"
        params.append(tuple(subjects)) 
    
    if min_age:
        query += " AND age_group >= %s"
        params.append(min_age)
    
    if max_age:
        query += " AND age_group <= %s"
        params.append(max_age)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            methods = cursor.fetchall()

        return methods
    except Exception as e:
        print(f"Error fetching methods: {str(e)}")
        return []
