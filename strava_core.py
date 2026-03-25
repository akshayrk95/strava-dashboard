"""
strava_core.py
All Strava data-fetching and computation logic.
Imported by app.py — no HTML, no Streamlit here.
"""

import os
import requests
from datetime import datetime, timedelta, date
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIG  (read from environment / Streamlit secrets)
# ─────────────────────────────────────────────
STRAVA_CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID",     "YOUR_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "YOUR_REFRESH_TOKEN")

YEAR_START     = date(2026, 1, 1)
YEAR_GOAL_DAYS = 365

WORKOUT_TYPES = {
    "WeightTraining", "Workout", "Yoga", "Pilates", "CrossFit",
    "Elliptical", "StairStepper", "RockClimbing", "Swim", "Ride",
    "VirtualRide", "Hike", "Walk",
}

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def get_access_token():
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

# ─────────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────────

def fetch_activities(token):
    activities = []
    page = 1
    headers  = {"Authorization": f"Bearer {token}"}
    after_ts = int(datetime(2026, 1, 1).timestamp())

    while True:
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page, "after": after_ts},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        activities.extend(batch)
        page += 1

    return activities

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def to_date(a):
    return datetime.fromisoformat(
        a["start_date_local"].replace("Z", "+00:00")
    ).date()

def km(a):
    return a.get("distance", 0) / 1000

def duration_min(a):
    return a.get("moving_time", 0) / 60

def pace_min_per_km(a):
    d, t = km(a), duration_min(a)
    return t / d if d > 0 else None

def elevation(a):
    return a.get("total_elevation_gain", 0)

def heartrate(a):
    return a.get("average_heartrate")

def format_pace(p):
    if not p:
        return "-"
    m = int(p)
    s = int((p % 1) * 60)
    return f"{m}:{s:02d} /km"

def format_duration(mins):
    h = int(mins // 60)
    m = int(mins % 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"

# ─────────────────────────────────────────────
# STREAKS
# ─────────────────────────────────────────────

def compute_streaks(activities):
    dates     = sorted(set(to_date(a) for a in activities))
    today     = date.today()
    has_today = today in dates
    start_day = today if has_today else today - timedelta(days=1)

    streak = 0
    d = start_day
    while d in dates:
        streak += 1
        d -= timedelta(days=1)

    longest = cur = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            cur += 1
        else:
            cur = 1
        longest = max(longest, cur)
    longest = max(longest, cur)

    return streak, longest, has_today

# ─────────────────────────────────────────────
# WEEKLY BREAKDOWN
# ─────────────────────────────────────────────

def weekly_breakdown(activities, n_weeks=12):
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    weeks      = []

    for i in range(n_weeks, 0, -1):
        ws = week_start - timedelta(weeks=i)
        we = ws + timedelta(days=6)
        week_acts = [a for a in activities if ws <= to_date(a) <= we]
        runs      = [a for a in week_acts if a.get("type") == "Run"]
        workouts  = [a for a in week_acts if a.get("type") in WORKOUT_TYPES]
        weeks.append({
            "label":             ws.strftime("W%U"),
            "start":             ws.isoformat(),
            "end":               we.isoformat(),
            "run_km":            round(sum(km(r) for r in runs), 1),
            "run_count":         len(runs),
            "workout_count":     len(workouts),
            "active_days":       len(set(to_date(a) for a in week_acts)),
            "total_duration_min":round(sum(duration_min(a) for a in week_acts), 0),
            "elevation_m":       round(sum(elevation(r) for r in runs), 0),
        })
    return weeks

# ─────────────────────────────────────────────
# MONTHLY BREAKDOWN
# ─────────────────────────────────────────────

def monthly_breakdown(activities):
    today  = date.today()
    months = []
    d      = date(2026, 1, 1)

    while d <= today:
        m_start = d
        if d.month == 12:
            m_end = date(d.year + 1, 1, 1) - timedelta(days=1)
        else:
            m_end = date(d.year, d.month + 1, 1) - timedelta(days=1)
        m_end = min(m_end, today)

        m_acts   = [a for a in activities if m_start <= to_date(a) <= m_end]
        runs     = [a for a in m_acts if a.get("type") == "Run"]
        workouts = [a for a in m_acts if a.get("type") in WORKOUT_TYPES]

        days_in_period = (m_end - m_start).days + 1
        active_days    = len(set(to_date(a) for a in m_acts))
        paces          = [pace_min_per_km(r) for r in runs if pace_min_per_km(r)]
        hrs            = [heartrate(r) for r in runs if heartrate(r)]

        months.append({
            "label":             d.strftime("%b %Y"),
            "run_km":            round(sum(km(r) for r in runs), 1),
            "run_count":         len(runs),
            "workout_count":     len(workouts),
            "active_days":       active_days,
            "days_in_period":    days_in_period,
            "perfect":           active_days == days_in_period,
            "total_duration_min":round(sum(duration_min(a) for a in m_acts), 0),
            "elevation_m":       round(sum(elevation(r) for r in runs), 0),
            "avg_pace":          format_pace(sum(paces) / len(paces)) if paces else "-",
            "avg_hr":            round(sum(hrs) / len(hrs), 0) if hrs else "-",
        })

        d = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)

    return months

# ─────────────────────────────────────────────
# YEARLY SUMMARY
# ─────────────────────────────────────────────

def yearly_summary(activities):
    today       = date.today()
    day_of_year = (today - YEAR_START).days + 1

    runs     = [a for a in activities if a.get("type") == "Run"]
    workouts = [a for a in activities if a.get("type") in WORKOUT_TYPES]

    active_days     = len(set(to_date(a) for a in activities))
    total_km        = sum(km(r) for r in runs)
    total_elevation = sum(elevation(r) for r in runs)
    total_time_min  = sum(duration_min(a) for a in activities)

    paces    = [pace_min_per_km(r) for r in runs if pace_min_per_km(r)]
    avg_pace = sum(paces) / len(paces) if paces else None

    hrs    = [heartrate(r) for r in runs if heartrate(r)]
    avg_hr = round(sum(hrs) / len(hrs), 0) if hrs else None

    best_run   = max(runs, key=km, default=None)
    fastest_5k = None
    for r in runs:
        if km(r) >= 5:
            p = pace_min_per_km(r)
            if p and (fastest_5k is None or p < fastest_5k[0]):
                fastest_5k = (p, r)

    type_counts    = defaultdict(int)
    for a in activities:
        type_counts[a.get("type", "Unknown")] += 1

    pace_km_per_day = total_km / day_of_year
    projected_km    = pace_km_per_day * 365

    return {
        "day_of_year":       day_of_year,
        "active_days":       active_days,
        "missed_days":       day_of_year - active_days,
        "consistency_pct":   round(active_days / day_of_year * 100, 1),
        "total_km":          round(total_km, 1),
        "total_runs":        len(runs),
        "total_workouts":    len(workouts),
        "total_activities":  len(activities),
        "total_elevation_m": round(total_elevation, 0),
        "total_time_min":    round(total_time_min, 0),
        "avg_pace":          format_pace(avg_pace),
        "avg_hr":            avg_hr,
        "best_run_km":       round(km(best_run), 2) if best_run else 0,
        "best_run_date":     to_date(best_run).isoformat() if best_run else "-",
        "fastest_5k_pace":   format_pace(fastest_5k[0]) if fastest_5k else "-",
        "projected_year_km": round(projected_km, 0),
        "type_counts":       dict(type_counts),
        "avg_km_per_week":   round(total_km / max(1, day_of_year / 7), 1),
        "avg_run_distance":  round(total_km / max(1, len(runs)), 2),
    }

# ─────────────────────────────────────────────
# CURRENT WEEK + MONTH
# ─────────────────────────────────────────────

def current_period_stats(activities):
    today       = date.today()
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    this_week  = [a for a in activities if to_date(a) >= week_start]
    this_month = [a for a in activities if to_date(a) >= month_start]

    def stats(acts):
        runs     = [a for a in acts if a.get("type") == "Run"]
        workouts = [a for a in acts if a.get("type") in WORKOUT_TYPES]
        paces    = [pace_min_per_km(r) for r in runs if pace_min_per_km(r)]
        return {
            "run_km":            round(sum(km(r) for r in runs), 1),
            "run_count":         len(runs),
            "workout_count":     len(workouts),
            "active_days":       len(set(to_date(a) for a in acts)),
            "avg_pace":          format_pace(sum(paces) / len(paces)) if paces else "-",
            "total_duration_min":round(sum(duration_min(a) for a in acts), 0),
            "elevation_m":       round(sum(elevation(r) for r in runs), 0),
        }

    return stats(this_week), stats(this_month)
