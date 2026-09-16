# LabPilot (Python / Streamlit)

A multi-page dashboard for running the 135B / 138B pharmacy labs at FCCU:
weekly schedule, per-course experiment planning, a lab-session tracker with
auto-detected "awaiting confirmation" sessions, daily notes & correspondence,
and a follow-up reminder list. All data lives in one SQLite file, so unlike
the earlier single-page HTML version, this one persists properly and can be
extended with real automation (scheduled imports, email reminders, etc.).

## Running it locally

```bash
cd labpilot_py
pip install -r requirements.txt
streamlit run app.py
```

It'll open in your browser at `http://localhost:8501`. The database is
created automatically on first run at `data/labpilot.db`, seeded with:
- The current corrected FA26 schedule for 135B/138B
- The chemical stock lists from your Expiry_date_file (both labs)

Lab ware isn't seeded yet — once you share that list, use the **Import
Data** page (Chemical/lab ware stock tab, set type to "labware") to load
it in, same as any future chemical stock refresh.

## Deploying so you can reach it from anywhere

Since you've already deployed a Streamlit app before, this follows the same
path:
1. Push this folder to a GitHub repo (private is fine).
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at
   that repo's `app.py`.
3. **Important**: `data/labpilot.db` will reset on redeploys on the free
   tier, since it isn't persistent storage. For anything beyond casual use,
   either:
   - Use Streamlit's built-in secrets + an external database (e.g. a free
     Postgres instance on Supabase/Neon) instead of local SQLite, or
   - Periodically export/download a backup (a "download the .db file"
     button is an easy thing to add next).

## Where the real automation lives

- **Weekly Schedule** page is the single source of truth — every other
  page reads from it, so a correction here (like the Mr. Shazad/Wednesday
  fix from before) propagates everywhere automatically.
- **Lab Tracker → Awaiting confirmation** recomputes on every page load by
  checking the current time against each slot's end time — no cron job
  needed, and it looks back two weeks, so nothing is lost if you don't log
  same-day.
- **Import Data** page has a parser already built for the exact shape of
  `PharmD_Labs_Schedule-FL26.xlsx` (the Classes/Lab header format) and the
  `Expiry_date_file.xlsx` chemical stock sheets — so next semester's files
  can be dropped in directly instead of being retyped by hand.

## Natural next steps (not built yet, flagging honestly)

- **Email reminders**: a scheduled script (cron, or a cloud function) that
  reads `followups` and `pending_confirmations()` and sends you a morning
  digest. The logic already exists in `lib.py` — this just needs a
  scheduler wrapped around it, which isn't possible from inside this chat
  environment.
- **Full auto-mapping** of the Classes/Lab schedule import directly into
  the Weekly Schedule grid (currently shows you the parsed rows and asks
  you to apply them manually, since period-label formats have already
  varied between the files you've shared).
- **Multi-user auth**, if this ever needs to be used by more than one
  demonstrator.
