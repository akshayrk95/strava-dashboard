# 🔥 Akshay's 2026 Fitness Dashboard

Live Strava dashboard built with Streamlit. Password-protected, auto-refreshes
every hour, switches between dark mode (20:00–06:00) and light mode (06:00–20:00).

---

## Files

```
strava_dashboard/
├── app.py                        ← Streamlit dashboard
├── strava_core.py                ← All data logic (no HTML)
├── requirements.txt              ← Python dependencies
├── .gitignore                    ← Keeps secrets safe
└── .streamlit/
    ├── config.toml               ← Theme & server config
    └── secrets.toml.example      ← Template — copy & fill in
```

---

## Step 1 — Get your Strava API credentials

1. Go to https://www.strava.com/settings/api
2. Create an app (name/website don't matter)
3. Copy your **Client ID** and **Client Secret**
4. Get your **Refresh Token**:
   - Use https://www.strava.com/oauth/authorize with scope `activity:read_all`
   - Or use a tool like https://developers.strava.com/docs/getting-started/

---

## Step 2 — Run locally first

```bash
# Install dependencies
pip install -r requirements.txt

# Create your secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Then edit .streamlit/secrets.toml with your real values

# Run
streamlit run app.py
```

Open http://localhost:8501 — enter your password and you're in.

---

## Step 3 — Deploy to Streamlit Cloud (free public URL)

### 3a. Push to GitHub

```bash
git init
git add app.py strava_core.py requirements.txt .streamlit/config.toml .gitignore
# ⚠️  Do NOT add secrets.toml — it's in .gitignore
git commit -m "Initial dashboard"
git remote add origin https://github.com/YOUR_USERNAME/strava-dashboard.git
git push -u origin main
```

### 3b. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch: `main` → file: `app.py`
5. Click **Advanced settings → Secrets** and paste:

```toml
STRAVA_CLIENT_ID     = "your_client_id"
STRAVA_CLIENT_SECRET = "your_client_secret"
STRAVA_REFRESH_TOKEN = "your_refresh_token"
YOUR_NAME            = "Akshay"
DASHBOARD_PASSWORD   = "your_chosen_password"
```

6. Click **Deploy** — you'll get a URL like:
   `https://akshay-fitness-2026.streamlit.app`

---

## Step 4 — Share with your followers

Your dashboard is password-protected. Share it like this on Instagram/Twitter:

> "My 2026 running stats are live 🔥
> [link] · password: running2026"

Anyone with the link + password can view — they can't edit anything.

---

## Security model

| Threat | Protection |
|---|---|
| Random people accessing your data | Password gate (HMAC constant-time compare) |
| Password brute force | Streamlit Cloud rate-limits connections |
| Secrets leaked via GitHub | `.gitignore` excludes `secrets.toml`; real secrets live in Streamlit Cloud secrets manager |
| Strava token exposure | Token never sent to browser; all API calls are server-side |

This is read-only public sharing — appropriate for a fitness journey dashboard.
For higher security, use Streamlit's built-in `st.experimental_user` with Google OAuth.

---

## Customisation

| What | Where |
|---|---|
| Dark/light mode hours | `app.py` line: `is_dark = hour >= 20 or hour < 6` |
| Refresh interval | `app.py`: `REFRESH_HOURS = 1` |
| Year goal / start date | `strava_core.py`: `YEAR_START`, `YEAR_GOAL_DAYS` |
| Add workout types | `strava_core.py`: `WORKOUT_TYPES` set |
| Dashboard password | Streamlit Cloud secrets: `DASHBOARD_PASSWORD` |
