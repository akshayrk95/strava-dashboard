import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
import time
import os
import hashlib
import hmac

# ── Import all data logic from strava_core ──────────────────────────────────
from strava_core import (
    get_access_token, fetch_activities,
    compute_streaks, weekly_breakdown, monthly_breakdown,
    yearly_summary, current_period_stats,
    format_pace, format_duration, to_date, km, WORKOUT_TYPES,
)

# ─────────────────────────────────────────────
# CONFIG  (set these in Streamlit Cloud secrets)
# ─────────────────────────────────────────────
YOUR_NAME      = os.getenv("YOUR_NAME", "Akshay")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASSWORD", "changeme123")  # set in secrets
REFRESH_HOURS  = 1   # cache TTL

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title=f"{YOUR_NAME} · 2026 Fitness",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# AUTO DARK / LIGHT MODE BASED ON TIME OF DAY
# 06:00–20:00 → light   |   20:00–06:00 → dark
# ─────────────────────────────────────────────
hour = datetime.now().hour
is_dark = hour >= 20 or hour < 6

if is_dark:
    bg         = "#0a0a0f"
    surface    = "#13131a"
    surface2   = "#1c1c28"
    border     = "#2a2a3d"
    text       = "#f0f0f5"
    muted      = "#6b6b8a"
    orange     = "#ff5c00"
    green      = "#00e676"
    blue       = "#448aff"
    red        = "#ff4444"
    plot_template = "plotly_dark"
    mode_label = "🌙 Night mode"
else:
    bg         = "#f8f7f4"
    surface    = "#ffffff"
    surface2   = "#f0ede8"
    border     = "#e0dbd4"
    text       = "#1a1a2e"
    muted      = "#6b7280"
    orange     = "#e84f00"
    green      = "#00875a"
    blue       = "#1d5fb4"
    red        = "#dc2626"
    plot_template = "plotly_white"
    mode_label = "☀️ Day mode"

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&family=JetBrains+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] {{
    background-color: {bg} !important;
    color: {text} !important;
    font-family: 'DM Sans', sans-serif;
  }}

  /* Hide Streamlit chrome */
  #MainMenu, footer, header {{ visibility: hidden; }}
  .block-container {{ padding-top: 1.5rem !important; max-width: 1200px; }}

  /* Metric cards */
  .stat-card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    position: relative;
    overflow: hidden;
    height: 100%;
  }}
  .stat-card .label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: {muted};
    margin-bottom: 0.3rem;
  }}
  .stat-card .value {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.3rem;
    line-height: 1;
    color: {text};
  }}
  .stat-card .value.orange {{ color: {orange}; }}
  .stat-card .value.green  {{ color: {green};  }}
  .stat-card .value.blue   {{ color: {blue};   }}
  .stat-card .value.red    {{ color: {red};     }}
  .stat-card .sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: {muted};
    margin-top: 0.25rem;
  }}
  .stat-card .accent {{
    position: absolute;
    bottom: 0; left: 0;
    width: 100%; height: 3px;
  }}

  /* Section titles */
  .section-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 0.1em;
    color: {muted};
    text-transform: uppercase;
    border-bottom: 1px solid {border};
    padding-bottom: 0.4rem;
    margin: 1.5rem 0 0.8rem;
  }}

  /* Header */
  .hero-name {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(3rem, 7vw, 5.5rem);
    letter-spacing: 0.04em;
    line-height: 0.9;
    color: {text};
  }}
  .hero-name span {{ color: {orange}; }}
  .hero-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: {muted};
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 0.5rem;
  }}
  .streak-box {{
    background: {'rgba(255,92,0,0.12)' if is_dark else 'rgba(232,79,0,0.08)'};
    border: 1.5px solid {orange};
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: center;
  }}
  .streak-num {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: {orange};
    line-height: 1;
  }}
  .streak-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: {muted};
    text-transform: uppercase;
    letter-spacing: 0.15em;
  }}

  /* Warning banner */
  .warn-banner {{
    background: {'rgba(255,92,0,0.1)' if is_dark else 'rgba(232,79,0,0.07)'};
    border: 1px solid {orange};
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: {muted};
    margin-bottom: 1rem;
  }}
  .warn-banner strong {{ color: {orange}; }}

  /* Perfect badge */
  .perfect {{ color: {green}; font-weight: 700; }}

  /* Mode pill */
  .mode-pill {{
    display: inline-block;
    background: {surface2};
    border: 1px solid {border};
    border-radius: 20px;
    padding: 3px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: {muted};
  }}

  /* Plotly chart background fix */
  .js-plotly-plot .plotly, .js-plotly-plot .plotly div {{
    background: transparent !important;
  }}

  /* Table */
  .styled-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
  }}
  .styled-table th {{
    text-align: left;
    padding: 0.4rem 0.7rem;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: {muted};
    border-bottom: 1px solid {border};
  }}
  .styled-table td {{
    padding: 0.5rem 0.7rem;
    border-bottom: 1px solid {'rgba(255,255,255,0.04)' if is_dark else 'rgba(0,0,0,0.05)'};
    color: {text};
  }}
  .styled-table tr:hover td {{
    background: {surface2};
  }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PASSWORD GATE
# ─────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.markdown(f"""
    <div style="max-width:360px;margin:6rem auto;background:{surface};
         border:1px solid {border};border-radius:16px;padding:2.5rem;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;
           color:{orange};text-align:center;margin-bottom:0.3rem;">
        {YOUR_NAME.upper()}
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
           color:{muted};text-align:center;text-transform:uppercase;
           letter-spacing:0.12em;margin-bottom:1.5rem;">
        2026 Fitness Dashboard
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login"):
        pwd = st.text_input("Password", type="password", placeholder="Enter access password")
        submitted = st.form_submit_button("Enter →", use_container_width=True)
        if submitted:
            # Constant-time comparison to prevent timing attacks
            if hmac.compare_digest(pwd.encode(), DASHBOARD_PASS.encode()):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


# ─────────────────────────────────────────────
# CACHED DATA FETCH  (1 hour TTL)
# ─────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_HOURS * 3600, show_spinner=False)
def load_all_data():
    token      = get_access_token()
    activities = fetch_activities(token)
    if not activities:
        return None

    streak, longest, has_today = compute_streaks(activities)
    yearly     = yearly_summary(activities)
    weekly     = weekly_breakdown(activities, n_weeks=12)
    monthly    = monthly_breakdown(activities)
    week_stats, month_stats = current_period_stats(activities)

    return {
        "activities":   activities,
        "streak":       streak,
        "longest":      longest,
        "has_today":    has_today,
        "yearly":       yearly,
        "weekly":       weekly,
        "monthly":      monthly,
        "week_stats":   week_stats,
        "month_stats":  month_stats,
        "fetched_at":   datetime.now(),
    }


# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
CHART_CONFIG = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="JetBrains Mono", color=muted, size=11),
    showlegend=True,
    legend=dict(font=dict(color=muted, size=10), bgcolor="rgba(0,0,0,0)"),
)

def axis_style(title=""):
    return dict(
        gridcolor=border,
        linecolor=border,
        tickfont=dict(color=muted, size=10),
        title=dict(text=title, font=dict(color=muted, size=10)),
        zeroline=False,
    )


def weekly_km_chart(weekly):
    labels = [w["label"] for w in weekly]
    values = [w["run_km"] for w in weekly]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=orange,
        marker_line_width=0,
        hovertemplate="%{x}: <b>%{y} km</b><extra></extra>",
    ))
    fig.update_layout(**CHART_CONFIG, height=220,
                      xaxis=axis_style(), yaxis=axis_style("km"))
    return fig


def monthly_combo_chart(monthly):
    labels  = [m["label"] for m in monthly]
    km_vals = [m["run_km"] for m in monthly]
    day_vals= [m["active_days"] for m in monthly]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=km_vals, name="KM Run",
        marker_color=orange, marker_line_width=0,
        yaxis="y1",
        hovertemplate="%{x}: <b>%{y} km</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=day_vals, name="Active Days",
        line=dict(color=green, width=2.5),
        mode="lines+markers",
        marker=dict(color=green, size=6),
        yaxis="y2",
        hovertemplate="%{x}: <b>%{y} days</b><extra></extra>",
    ))
    fig.update_layout(
        **CHART_CONFIG, height=250,
        yaxis=dict(**axis_style("KM"), side="left"),
        yaxis2=dict(**axis_style("Days"), side="right", overlaying="y", showgrid=False),
        xaxis=axis_style(),
        barmode="group",
    )
    return fig


def activity_split_chart(type_counts):
    labels = list(type_counts.keys())
    values = list(type_counts.values())

    colors = [orange, blue, green, "#ffaa00", "#c864ff", "#00bcd4",
              "#ff6b9d", "#a8edea", "#fed9b7"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors[:len(labels)], line=dict(width=0)),
        textfont=dict(color=muted, size=10),
        hovertemplate="%{label}: <b>%{value}</b> (%{percent})<extra></extra>",
    ))

    # 🔥 FIX: override legend safely
    layout = dict(CHART_CONFIG)
    layout["legend"] = dict(
        font=dict(color=muted, size=10),
        bgcolor="rgba(0,0,0,0)",
        orientation="v",
        yanchor="middle", y=0.5,
        xanchor="left", x=1.0
    )

    fig.update_layout(**layout, height=220)

    return fig


def weekly_split_chart(weekly):
    labels   = [w["label"] for w in weekly]
    runs     = [w["run_count"] for w in weekly]
    workouts = [w["workout_count"] for w in weekly]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=runs, name="Runs",
                         marker_color=orange, marker_line_width=0,
                         hovertemplate="%{x}: <b>%{y} runs</b><extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=workouts, name="Workouts",
                         marker_color=blue, marker_line_width=0,
                         hovertemplate="%{x}: <b>%{y} workouts</b><extra></extra>"))
    fig.update_layout(**CHART_CONFIG, height=220,
                      barmode="stack",
                      xaxis=axis_style(), yaxis=axis_style("count"))
    return fig


def consistency_heatmap(activities):
    today = date.today()
    year_start = date(2026, 1, 1)
    active_dates = set(to_date(a) for a in activities)

    weeks = []
    d = year_start - timedelta(days=year_start.weekday())
    while d <= today + timedelta(days=6):
        week = []
        for i in range(7):
            day = d + timedelta(days=i)
            if day < year_start or day > today:
                week.append(None)
            elif day in active_dates:
                week.append(1)
            else:
                week.append(0)
        weeks.append(week)
        d += timedelta(weeks=1)

    z = [[weeks[col][row] for col in range(len(weeks))] for row in range(7)]
    x = [str(i) for i in range(len(weeks))]
    y = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    colorscale = [
        [0.0, border],
        [0.5, border],
        [0.5, orange],
        [1.0, orange],
    ]

    fig = go.Figure(go.Heatmap(
        z=z, x=x, y=y,
        colorscale=colorscale,
        showscale=False,
        xgap=3, ygap=3,
        hovertemplate="<b>%{y}</b><extra></extra>",
        zmin=0, zmax=1,
    ))

    fig.update_layout(
        **CHART_CONFIG,
        height=160,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(
            tickfont=dict(color=muted, size=9),
            showgrid=False,
            zeroline=False,
            side="left"
        ),
        margin=dict(l=30, r=0, t=10, b=0),  # ✅ now safe
    )

    return fig


# ─────────────────────────────────────────────
# STAT CARD HTML
# ─────────────────────────────────────────────
def card(label, value, sub="", color="", accent_color=None):
    accent = accent_color or (
        orange if color == "orange" else
        green  if color == "green"  else
        blue   if color == "blue"   else
        red    if color == "red"    else border
    )
    return f"""
    <div class="stat-card">
      <div class="label">{label}</div>
      <div class="value {color}">{value}</div>
      {'<div class="sub">' + sub + '</div>' if sub else ''}
      <div class="accent" style="background:{accent}"></div>
    </div>
    """


# ─────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────
def render_dashboard(data):
    yr   = data["yearly"]
    ws   = data["week_stats"]
    ms   = data["month_stats"]
    mon  = data["monthly"]
    wk   = data["weekly"]
    acts = data["activities"]

    streak      = data["streak"]
    longest     = data["longest"]
    has_today   = data["has_today"]
    fetched_at  = data["fetched_at"]
    perfect_months = sum(1 for m in mon if m["perfect"])
    today = date.today()

    # ── HEADER ─────────────────────────────────
    h_col, s_col = st.columns([3, 1])
    with h_col:
        name_parts = YOUR_NAME.upper().split()
        first = name_parts[0]
        rest  = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        st.markdown(f"""
        <div class="hero-name">{first}<br/><span>2026</span>{(' ' + rest) if rest else ''}</div>
        <div class="hero-sub">
          Fitness Year in Progress &nbsp;·&nbsp; Updated {today.strftime('%b %d, %Y')}
          &nbsp;&nbsp;<span class="mode-pill">{mode_label}</span>
        </div>
        """, unsafe_allow_html=True)

    with s_col:
        emoji = "🔥" if has_today else "⚡"
        st.markdown(f"""
        <div class="streak-box">
          <div class="streak-num">{emoji}{streak}</div>
          <div class="streak-label">Day Streak</div>
          <div class="streak-label" style="margin-top:0.2rem;color:{muted}">
            Best: {longest} days
          </div>
        </div>
        """, unsafe_allow_html=True)

    if not has_today:
        st.markdown(f"""
        <div class="warn-banner">
          ⚡ <strong>Today's activity not yet logged.</strong> Keep the streak alive!
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
         color:{muted};text-align:right;margin-top:-0.5rem;margin-bottom:0.5rem;">
      Data refreshes every hour &nbsp;·&nbsp; Last fetched {fetched_at.strftime('%H:%M')}
    </div>
    """, unsafe_allow_html=True)

    # ── YEAR AT A GLANCE ────────────────────────
    st.markdown('<div class="section-title">📅 2026 At a Glance</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    ebc_pct = round(yr["total_elevation_m"] / 5364 * 100, 0)
    with c1:
        st.markdown(card("Total KM Run", f"{yr['total_km']}",
                         f"Proj. {int(yr['projected_year_km'])} km by Dec 31", "orange"), unsafe_allow_html=True)
    with c2:
        st.markdown(card("Active Days", str(yr["active_days"]),
                         f"of {yr['day_of_year']} days · {yr['consistency_pct']}% consistent", "green"), unsafe_allow_html=True)
    with c3:
        st.markdown(card("Total Activities", str(yr["total_activities"]),
                         f"{yr['total_runs']} runs · {yr['total_workouts']} workouts"), unsafe_allow_html=True)
    with c4:
        st.markdown(card("Time Moving", format_duration(yr["total_time_min"]),
                         f"{int(yr['total_elevation_m'])}m elev · {ebc_pct:.0f}% to EBC", "blue"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(card("Avg Pace", yr["avg_pace"], "across all runs"), unsafe_allow_html=True)
    with c2:
        st.markdown(card("Avg KM / Week", f"{yr['avg_km_per_week']} km", "weekly average"), unsafe_allow_html=True)
    with c3:
        st.markdown(card("Perfect Months", str(perfect_months), "zero missed days", "orange"), unsafe_allow_html=True)
    with c4:
        missed_color = "red" if yr["missed_days"] > 0 else "green"
        st.markdown(card("Missed Days", str(yr["missed_days"]),
                         f"out of {yr['day_of_year']} days this year", missed_color), unsafe_allow_html=True)

    # ── RIGHT NOW ───────────────────────────────
    st.markdown('<div class="section-title">⚡ Right Now</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(card("This Week",
                         f"{ws['run_km']} km",
                         f"{ws['run_count']} runs · {ws['workout_count']} workouts · "
                         f"{ws['active_days']} active days · {ws['avg_pace']} · "
                         f"{format_duration(ws['total_duration_min'])} total",
                         "orange"), unsafe_allow_html=True)
    with c2:
        st.markdown(card(f"This Month — {today.strftime('%B')}",
                         f"{ms['run_km']} km",
                         f"{ms['run_count']} runs · {ms['workout_count']} workouts · "
                         f"{ms['active_days']} active days · {ms['avg_pace']} · "
                         f"{format_duration(ms['total_duration_min'])} total",
                         "green"), unsafe_allow_html=True)

    # ── ACTIVITY HEATMAP ────────────────────────
    st.markdown('<div class="section-title">📆 Activity Heatmap — 2026</div>', unsafe_allow_html=True)
    st.plotly_chart(consistency_heatmap(acts), use_container_width=True, config={"displayModeBar": False})

    # ── WEEKLY CHART ────────────────────────────
    st.markdown('<div class="section-title">📈 Weekly KM (Last 12 Weeks)</div>', unsafe_allow_html=True)
    st.plotly_chart(weekly_km_chart(wk), use_container_width=True, config={"displayModeBar": False})

    # ── MONTHLY COMBO ───────────────────────────
    st.markdown('<div class="section-title">📊 Monthly Overview</div>', unsafe_allow_html=True)
    st.plotly_chart(monthly_combo_chart(mon), use_container_width=True, config={"displayModeBar": False})

    # ── SPLIT CHARTS ────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">🏃 Activity Type Split</div>', unsafe_allow_html=True)
        st.plotly_chart(activity_split_chart(yr["type_counts"]), use_container_width=True,
                        config={"displayModeBar": False})
    with c2:
        st.markdown('<div class="section-title">💪 Runs vs Workouts / Week</div>', unsafe_allow_html=True)
        st.plotly_chart(weekly_split_chart(wk), use_container_width=True, config={"displayModeBar": False})

    # ── MONTHLY TABLE ───────────────────────────
    st.markdown('<div class="section-title">🗓 Month-by-Month Breakdown</div>', unsafe_allow_html=True)
    rows = ""
    for m in mon:
        perfect_html = '<span class="perfect">PERFECT ✓</span>' if m["perfect"] else "—"
        rows += (
            f"<tr>"
            f"<td><strong>{m['label']}</strong></td>"
            f"<td>{m['run_km']} km</td>"
            f"<td>{m['run_count']}</td>"
            f"<td>{m['workout_count']}</td>"
            f"<td>{m['active_days']} / {m['days_in_period']}</td>"
            f"<td>{m['avg_pace']}</td>"
            f"<td>{int(m['elevation_m'])}m</td>"
            f"<td>{perfect_html}</td>"
            f"</tr>"
        )
    st.markdown(f"""
    <table class="styled-table">
      <thead><tr>
        <th>Month</th><th>KM</th><th>Runs</th><th>Workouts</th>
        <th>Active Days</th><th>Avg Pace</th><th>Elevation</th><th>Status</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # ── FUN FACTS ───────────────────────────────
    st.markdown('<div class="section-title">🎯 Fun Facts</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    everest_pct = round(yr["total_elevation_m"] / 8849 * 100, 1)
    avg_hr_str  = f"{int(yr['avg_hr'])} bpm" if yr["avg_hr"] else "N/A"
    with c1:
        st.markdown(card("Best Single Run", f"{yr['best_run_km']} km",
                         yr["best_run_date"], "green"), unsafe_allow_html=True)
    with c2:
        st.markdown(card("Fastest 5K Pace", yr["fastest_5k_pace"],
                         "best pace over a 5km+ run", "blue"), unsafe_allow_html=True)
    with c3:
        st.markdown(card("Avg Heart Rate", avg_hr_str,
                         "average across all runs"), unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(card("Avg Run Distance", f"{yr['avg_run_distance']} km",
                         "per run"), unsafe_allow_html=True)
    with c2:
        st.markdown(card("% of Everest", f"{everest_pct}%",
                         f"{int(yr['total_elevation_m'])}m of 8,849m gained"), unsafe_allow_html=True)
    with c3:
        st.markdown(card("Longest Streak", f"{longest} days",
                         "consecutive active days", "orange"), unsafe_allow_html=True)

    # ── FOOTER ──────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;font-family:'JetBrains Mono',monospace;
         font-size:0.65rem;color:{muted};padding:2rem 0 1rem;
         border-top:1px solid {border};margin-top:2rem;text-transform:uppercase;
         letter-spacing:0.1em;">
      {YOUR_NAME} · 2026 Fitness Dashboard · Data from Strava · Keep Moving
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def main():

    with st.spinner("Fetching your Strava data..."):
        data = load_all_data()

    if data is None:
        st.error("No activities found. Check your Strava credentials.")
        return

    render_dashboard(data)

    # ✅ Removed time.sleep() — Streamlit cache handles refresh


if __name__ == "__main__":
    main()
