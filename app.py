import streamlit as st
from datetime import date, datetime, timedelta

from db import init_db, DAYS, ROOMS, slot_label
import lib

st.set_page_config(page_title="LabPilot", page_icon="🧪", layout="wide")
init_db()

st.title("🧪 LabPilot")
st.caption("135B / 138B · FCCU · Fall '26")

# ---------- Backup reminder ----------
backup_days = lib.days_since_backup()
if backup_days is None:
    st.error("⚠️ No backup has ever been taken. This app's data does NOT survive a redeploy "
             "on Streamlit Cloud's free tier — go to **Backup & Restore** before making any "
             "changes.")
elif backup_days > 7:
    st.warning(f"⚠️ Last backup was {backup_days} days ago. Head to **Backup & Restore** "
               "before pushing any code changes.")

# ---------- Right now ----------
now = datetime.now()
today_name = DAYS[now.weekday()] if now.weekday() < 5 else None

st.subheader("Right now")
if not today_name:
    st.info("It's the weekend — no labs scheduled.")
else:
    sessions = lib.current_sessions(now)
    cols = st.columns(len(ROOMS))
    for col, room in zip(cols, ROOMS):
        with col:
            s = sessions[room]
            if s:
                st.success(f"**{room}**\n\n{s['course']} ({s['section']})\n\n{s['instructor']}")
            else:
                st.info(f"**{room}**\n\nFree right now")

st.divider()

# ---------- At-a-glance metrics ----------
pending = lib.pending_confirmations()
overdue = lib.overdue_followups()
open_fu = lib.open_followups()
week_start, week_end = lib.week_range()
week_entries = lib.get_entries(date_from=week_start, date_to=week_end)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Labs awaiting confirmation", len(pending))
m2.metric("Open follow-ups", len(open_fu), delta=f"{len(overdue)} overdue" if overdue else None,
          delta_color="inverse")
m3.metric("Entries this week", len(week_entries))
m4.metric("Today", now.strftime("%a, %d %b"))

st.divider()

# ---------- Overdue follow-ups banner ----------
if overdue:
    st.subheader("⚠️ Overdue follow-ups")
    for f in overdue:
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"**{f['title']}** — due {f['due_date']}  \n{f['body'] or ''}")
        with c2:
            if st.button("Mark done", key=f"home_done_{f['id']}"):
                lib.mark_followup(f["id"], "done")
                st.rerun()
    st.divider()

# ---------- Pending confirmations preview ----------
if pending:
    st.subheader("🧪 Labs waiting to be logged")
    st.caption("Head to the Lab Tracker page to fill these in — no need to do it same-day, "
               "batch them at the end of the week.")
    for p in pending[:5]:
        st.markdown(f"- **{p['course']}** ({p['section']}) — {p['instructor']} · "
                    f"{p['day']} {p['date']} · {p['room']} · {p['slot_label']}")
    if len(pending) > 5:
        st.caption(f"...and {len(pending) - 5} more.")
    st.divider()

# ---------- Today's full schedule ----------
st.subheader("Today's schedule" if today_name else "Monday's schedule (next teaching day)")
show_day = today_name or "Monday"
cols = st.columns(len(ROOMS))

for col, room in zip(cols, ROOMS):
    with col:
        st.markdown(f"**{room}**")
        df = lib.get_schedule_df()
        day_rows = df[(df["day"] == show_day) & (df["room"] == room)].sort_values("slot_start")
        if day_rows.empty:
            st.caption("Nothing scheduled.")
        for _, r in day_rows.iterrows():
            label = slot_label(r["slot_start"], r["slot_end"])
            if r["course"]:
                st.markdown(f"`{label}`  \n{r['course']} ({r['section']}) — {r['instructor']}")
            else:
                st.markdown(f"`{label}`  \n*Free*")

st.divider()
st.caption("Use the sidebar to jump to Weekly Schedule, Experiments, Lab Tracker, Notes & "
           "Follow-ups, or Import Data.")
