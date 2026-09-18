import streamlit as st
from datetime import date

from db import init_db
import lib

st.set_page_config(page_title="Follow-ups — LabPilot", page_icon="✅", layout="wide")
init_db()

st.title("✅ Follow-ups")
st.caption("Every project you've started or correspondence you're waiting on. This is the "
           "list that keeps things from quietly falling through the cracks.")

with st.expander("➕ Add a follow-up", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("What needs following up?",
                               placeholder="e.g. Confirm reagent order with vendor")
        category = st.selectbox("Category", ["project", "correspondence", "other"])
    with c2:
        due = st.date_input("Remind me by", value=None)
        description = st.text_area("Details (optional)")

    if st.button("Add follow-up", type="primary"):
        if not title.strip():
            st.warning("Give it a title first.")
        else:
            lib.add_followup(title.strip(), category, description.strip(),
                              due.isoformat() if due else None)
            st.success("Added.")
            st.rerun()

st.divider()

overdue = lib.overdue_followups()
if overdue:
    st.subheader(f"⚠️ Overdue ({len(overdue)})")
    for f in overdue:
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1:
            st.markdown(f"**{f['title']}** — due {f['due_date']} · _{f['category']}_")
            if f["description"]:
                st.caption(f["description"])
        with c2:
            if st.button("Done", key=f"od_done_{f['id']}"):
                lib.mark_followup(f["id"], "done")
                st.rerun()
        with c3:
            new_due = st.date_input("Snooze to", key=f"od_snooze_{f['id']}", label_visibility="collapsed")
            if st.button("Snooze", key=f"od_snoozebtn_{f['id']}"):
                lib.snooze_followup(f["id"], new_due.isoformat())
                st.rerun()
    st.divider()

open_items = [f for f in lib.get_followups("open") if f not in overdue]
st.subheader(f"Open ({len(open_items)})")
if not open_items:
    st.caption("Nothing open — you're all caught up.")
for f in open_items:
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        due_str = f" — due {f['due_date']}" if f["due_date"] else ""
        st.markdown(f"**{f['title']}**{due_str} · _{f['category']}_")
        if f["description"]:
            st.caption(f["description"])
    with c2:
        if st.button("Done", key=f"open_done_{f['id']}"):
            lib.mark_followup(f["id"], "done")
            st.rerun()
    with c3:
        new_due = st.date_input("Reschedule", key=f"open_snooze_{f['id']}", label_visibility="collapsed")
        if st.button("Update", key=f"open_snoozebtn_{f['id']}"):
            lib.snooze_followup(f["id"], new_due.isoformat())
            st.rerun()

with st.expander(f"Completed"):
    done_items = lib.get_followups("done")
    if not done_items:
        st.caption("Nothing completed yet.")
    for f in done_items:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"~~{f['title']}~~ · _{f['category']}_ · completed {f['last_touched']}")
        if c2.button("Reopen", key=f"reopen_{f['id']}"):
            lib.mark_followup(f["id"], "open")
            st.rerun()
