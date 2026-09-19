# LabPilot (Python / Streamlit)

A multi-page dashboard for running the 135B / 138B pharmacy labs at FCCU:
weekly schedule, per-course experiment planning, a lab-session tracker with
auto-detected "awaiting confirmation" sessions, and a unified color-coded
feed for notes, correspondence, and follow-up reminders. All data lives in
one SQLite file.

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

## Uploading to GitHub

Page filenames are plain ASCII on purpose (no emoji) — GitHub's web upload
can mangle unicode filenames, which is what broke the sidebar the first
time around. Each page still sets its own icon via `page_icon` in
`st.set_page_config`, so nothing is lost cosmetically.

If you're uploading via the GitHub web UI rather than git:
1. Create the repo, upload `app.py`, `requirements.txt`, `README.md` at
   the root.
2. Add file → Create new file → type `pages/1_Weekly_Schedule.py` as the
   name (the slash makes GitHub create the folder automatically), paste
   in the file's contents, commit. Repeat for the other 4 page files.
3. Same for `data/seed_inventory.csv` — type `data/seed_inventory.csv` as
   the filename when creating it.

## Deploying so you can reach it from anywhere

1. Push this folder to a GitHub repo (private is fine).
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at
   that repo's `app.py`.
3. **Important**: `data/labpilot.db` will reset on redeploys on the free
   tier, since it isn't persistent storage. For anything beyond casual use,
   either use an external database (e.g. a free Postgres instance on
   Supabase/Neon) instead of local SQLite, or periodically export/download
   a backup.

## The unified Notes / Correspondence / Follow-ups page

One table (`entries`) holds all three. A follow-up is just an entry with
`entry_type='followup'` plus a `due_date` and `status`; notes and
correspondence leave those blank. This is what lets the page show
everything from a given week in one color-coded scroll — blue for notes,
purple for correspondence, amber for follow-ups — instead of three
separate places to check. Still-open follow-ups from before the current
week stay surfaced too, so nothing drops off just because the week rolled
over.

## Where the real automation lives

- **Weekly Schedule** page is the single source of truth — every other
  page reads from it, so a correction here propagates everywhere.
- **Lab Tracker → Awaiting confirmation** recomputes on every page load by
  checking the current time against each slot's end time — no cron job
  needed, and it looks back two weeks, so nothing is lost if you don't log
  same-day.
- **Import Data** page has a parser already built for the exact shape of
  `PharmD_Labs_Schedule-FL26.xlsx` (the Classes/Lab header format) and the
  `Expiry_date_file.xlsx` chemical stock sheets.

## Natural next steps (not built yet, flagging honestly)

- **Email reminders**: a scheduled script reading `overdue_followups()`
  and `pending_confirmations()` to send a morning digest — the logic
  already exists in `lib.py`, this just needs a scheduler wrapped around
  it, which isn't possible from inside a chat environment.
- **Full auto-mapping** of the Classes/Lab schedule import directly into
  the Weekly Schedule grid.
- **Multi-user auth**, if this ever needs more than one demonstrator.
