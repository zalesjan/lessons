from datetime import date
import json

#def generate_lesson_plan(filters, subject_categories):
#    subject = filters.get('subject')
#    category = filters.get('category')
#    min_age = filters.get('min_age')
#    max_age = filters.get('max_age')
#    max_duration = filters.get('max_duration')
#
## Build subject list based on category if no subject is directly selected
#if category and not subject:
#    subjects = subject_categories.get(category, [])
#else:
#    subjects = [subject] if subject else []
#
#    # Build the query with dynamic filters
#    query = """
#    SELECT method_id, method_name, description, duration, age_group, block, subject, topic, tools, sources 
#    FROM test_db.DidacticMethods 
#    WHERE 1=1"""
#    params = []
#
#    if subjects:
#        query += " AND subject IN %s"
#        params.append(tuple(subjects)) 
#    
#    if min_age:
#        query += " AND age_group >= %s"
#        params.append(min_age)
#    
#    if max_age:
#        query += " AND age_group <= %s"
#        params.append(max_age)
#
#    try:
#        with get_db_connection() as conn:
#            cursor = conn.cursor()
#            cursor.execute(query, params)
#            methods = cursor.fetchall()
#
#        return methods
#    except Exception as e:
#        print(f"Error fetching methods: {str(e)}")
#        return []

#
#
from datetime import date, datetime

def reset_quotas_if_needed(profile):
    today = date.today()
    updated_fields = {}

    # --- DAILY ---
    last_daily = profile.get("last_quota_reset_daily")
    if not last_daily or last_daily != today:
        updated_fields["lessons_used_daily"] = 0
        updated_fields["last_quota_reset_daily"] = today

    # --- WEEKLY ---
    current_week = today.isocalendar()[1]
    last_week = None
    if profile.get("last_quota_reset_weekly"):
        last_week = profile["last_quota_reset_weekly"].isocalendar()[1]

    if not last_week or last_week != current_week:
        updated_fields["lessons_used_weekly"] = 0
        updated_fields["last_quota_reset_weekly"] = today

    # --- MONTHLY ---
    current_month = today.month
    last_month = None
    if profile.get("last_quota_reset_monthly"):
        last_month = profile["last_quota_reset_monthly"].month

    if not last_month or last_month != current_month:
        updated_fields["lessons_used_monthly"] = 0
        updated_fields["last_quota_reset_monthly"] = today

    # If nothing changed, return the original
    if not updated_fields:
        return profile

    # Merge changes into profile dict
    profile.update(updated_fields)
    return profile

def can_generate_lesson(profile, plan):

    profile = reset_quotas_if_needed(profile)

    daily   = profile.get("lessons_used_daily", 0)
    weekly  = profile.get("lessons_used_weekly", 0)
    monthly = profile.get("lessons_used_monthly", 0)
    total   = profile.get("lessons_used_total", 0)

    q_daily   = plan.get("lesson_daily")
    q_weekly  = plan.get("lesson_weekly")
    q_monthly = plan.get("lesson_monthly")
    q_total   = plan.get("lesson_total")

    # Daily
    if q_daily is not None and daily >= q_daily:
        return False, "Daily quota exceeded"

    # Weekly
    if q_weekly is not None and weekly >= q_weekly:
        return False, "Weekly quota exceeded"

    # Monthly
    if q_monthly is not None and monthly >= q_monthly:
        return False, "Monthly quota exceeded"

    # Total (lifetime)
    if q_total is not None and total >= q_total:
        return False, "Total quota exceeded"

    return True, ""

#
#def how_many_methods(profile, plan, ):
#    if profile == None:
#        number_of_methods_to_show = plan.get("weekly_method_quota")
#    elif profile.get("plan") == "free":
#        number_of_methods_to_show = free_plan_number_of_methods_to_show
#    return number_of_methods_to_show
#
def record_generation(profile):
    profile["lessons_used_daily"]   = profile.get("lessons_used_daily", 0) + 1
    profile["lessons_used_weekly"]  = profile.get("lessons_used_weekly", 0) + 1
    profile["lessons_used_monthly"] = profile.get("lessons_used_monthly", 0) + 1
    profile["lessons_used_total"]   = profile.get("lessons_used_total", 0) + 1

    profile["last_generation_date"] = date.today()

    return profile


def method_lang(id_value):
    """Extracts the language code after the second hyphen."""
    if not id_value or '-' not in id_value:
        return 'en'
    parts = id_value.split('-')
    return parts[-1] if len(parts[-1]) == 2 else 'en'

def safe_json_load(x):
    if not x or x in ("", "null", "None"):
        return []
    if isinstance(x, (list, dict)):
        return x
    try:
        return json.loads(x)
    except Exception:
        return [str(x)]
#            
#UPDATE profiles
#SET plan = 'free'
#WHERE subscription_expiry < CURRENT_DATE;

#
#def update_profile(user_id, data: dict):
    supabase.table("profiles").update(data).eq("id", user_id).execute()