from datetime import date, timedelta
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

def reset_quotas_if_needed(profile):
    today = date.today()
    updated_fields = {}

    # --- DAILY ---
    last_daily = profile.get("last_quota_reset_daily")
    if not last_daily or last_daily != today:
        updated_fields["lessons_used_daily"] = 0
        updated_fields["last_quota_reset_daily"] = today 
    # --- WEEKLY ---
    current_week = today
    last_week = None
    if profile.get("last_quota_reset_weekly"):
        last_week = profile["last_quota_reset_weekly"]

    if not last_week or last_week != current_week:
        updated_fields["lessons_used_weekly"] = 0
        updated_fields["last_quota_reset_weekly"] = today

    # --- MONTHLY ---
    current_month = today.month
    last_month = None
    if profile.get("last_quota_reset_monthly"):
        last_month = profile["last_quota_reset_monthly"]

    if not last_month or last_month != current_month:
        updated_fields["lessons_used_monthly"] = 0
        updated_fields["last_quota_reset_monthly"] = today

    # If nothing changed, return the original
    if not updated_fields:
        return profile
    
    for k, v in profile.items():
        if isinstance(v, date):
            profile[k] = v.isoformat()

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


def can_generate_guest(guest):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # reset week
    if guest["week_start"] != week_start:
        guest["ai_used_week"] = 0
        guest["week_start"] = week_start

    # reset month
    if guest["month_start"] != month_start:
        guest["ai_used_month"] = 0
        guest["month_start"] = month_start

    DAY_LIMIT = 3
    WEEK_LIMIT = 6
    MONTH_LIMIT = 9

 #   if guest["lessons_generated"] >= DAY_LIMIT:
 #       return False, True
    if guest["lessons_generated"] >= DAY_LIMIT:
        return False, True
    if guest["ai_used_week"] >= WEEK_LIMIT:
        return False, True
    if guest["ai_used_month"] >= MONTH_LIMIT:
        return False, True

    return True, None

def record_generation(profile: dict) -> dict:
    """
    Increment AI generation counters on a user profile.
    Ensures safe defaults, period resets (day/week/month),
    and stores ISO-formatted dates safe for JSON serialization.
    """

    # ✅ Always use today's local date instance
    _today = date.today() if callable(getattr(date, "today", None)) else date
    if callable(_today):
        _today = _today()
    iso_today = _today.isoformat()

    # Safely read last recorded generation date (if any)
    last_gen_str = profile.get("last_generation_date")
    try:
        last_gen = date.fromisoformat(last_gen_str) if last_gen_str else None
    except Exception:
        last_gen = None

    # Determine current week/month boundaries
    monday = _today - timedelta(days=_today.weekday())
    current_week_start = monday.isoformat()
    current_month_start = _today.replace(day=1).isoformat()

    # Read stored week/month boundaries, fall back to current
    last_week_start = profile.get("week_start") or current_week_start
    last_month_start = profile.get("month_start") or current_month_start

    # ---------- Period resets ----------
    # Reset daily when a new day starts
    if last_gen and last_gen != _today:
        profile["lessons_used_daily"] = 0

    if last_week_start != current_week_start:
        profile["lessons_used_weekly"] = 0
        profile["week_start"] = current_week_start

    if last_month_start != current_month_start:
        profile["lessons_used_monthly"] = 0
        profile["month_start"] = current_month_start

    # ---------- Increment counters ----------
    profile["lessons_used_daily"] = (profile.get("lessons_used_daily") or 0) + 1
    profile["lessons_used_weekly"] = (profile.get("lessons_used_weekly") or 0) + 1
    profile["lessons_used_monthly"] = (profile.get("lessons_used_monthly") or 0) + 1
    profile["lessons_used_total"] = (profile.get("lessons_used_total") or 0) + 1

        # ---------- Update date metadata ----------
    profile["last_generation_date"] = iso_today
    profile["last_quota_reset_daily"] = current_week_start  # store as string
    profile["last_quota_reset_weekly"] = current_week_start
    profile["last_quota_reset_monthly"] = current_month_start
    profile["last_generated_at"] = "now()"
   
 # ---------- Ensure all date objects are serialized ----------
    for k, v in profile.items():
        if isinstance(v, date):
            profile[k] = v.isoformat()
            
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
