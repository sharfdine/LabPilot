"""
One feed, three colors. A note, a piece of correspondence, and a follow-up
all live in the same table (see db.py) — the only real difference is that
a follow-up carries a due date and an open/done status. That's what makes
it possible to look back at the end of the week and see everything you did
and everyone you need to chase, in one scroll, without hopping between
separate pages.
"""

import streamlit as st
import calendar
from datetime import date, datetime

from db import init_db, ENTRY_TYPES
import lib

st.set_page_config(page_title="Notes & Follow-ups — LabPilot", page_icon="📝", layout="wide")
init_db()

st.title("📝 Notes, Correspondence & Follow-ups")
st.caption("Everything you jot down or need to chase, color-coded in one place.")

TYPE_STYLE = {
    "note":          {"bg": "#EFF6FF", "border": "#2563EB", "label": "📝 Note",          "chip": "#DBEAFE"},
    "correspondence":{"bg": "#F5F3FF", "border": "#7C3AED", "label": "✉️ Correspondence", "chip": "#EDE9FE"},
    "followup":      {"bg": "#FFFBEB", "border": "#D97706", "label": "⏰ Follow-up",       "chip": "#FEF3C7"},
}


def render_card(e, key_prefix):
    """Renders one color-coded entry card, plus action buttons appropriate
    to its type (delete for everything; mark-done/snooze for follow-ups)."""
    style = TYPE_STYLE[e["entry_type"]]
    due_line = ""
    if e["entry_type"] == "followup":
        status_word = "✅ Done" if e["status"] == "done" else "🔴 Overdue" if (
            e["due_date"] and e["due_date"] < date.today().isoformat() and e["status"] == "open"
        ) else "Open"
        due_line = f"<div style='font-size:12px;margin-top:4px;'><b>Due:</b> {e['due_date'] or '—'} · {status_word}</div>"

    st.markdown(f"""
    <div style="background:{style['bg']};border-left:5px solid {style['border']};
                padding:10px 14px;border-radius:8px;margin-bottom:6px;">
        <div style="font-size:11px;color:{style['border']};font-weight:700;letter-spacing:0.02em;">
            {style['label']} · {e['entry_date']}
        </div>
        <div style="font-weight:600;margin-top:3px;">{e['title'] or '(untitled)'}</div>
        <div style="margin-top:4px;font-size:14px;white-space:pre-wrap;">{e['body']}</div>
        {due_line}
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns([1, 1, 1, 5]) if e["entry_type"] == "followup" and e["status"] == "open" else st.columns([1, 8])

    if e["entry_type"] == "followup" and e["status"] == "open":
        with cols[0]:
            if st.button("Mark done", key=f"{key_prefix}_done_{e['id']}"):
                lib.mark_followup(e["id"], "done")
                st.rerun()
        with cols[1]:
            new_due = st.date_input("Snooze to", key=f"{key_prefix}_snoozedate_{e['id']}",
                                     label_visibility="collapsed")
            if st.button("Snooze", key=f"{key_prefix}_snoozebtn_{e['id']}"):
                lib.snooze_followup(e["id"], new_due.isoformat())
                st.rerun()
        with cols[2]:
            if st.button("Delete", key=f"{key_prefix}_del_{e['id']}"):
                lib.delete_entry(e["id"])
                st.rerun()
    else:
        with cols[0]:
            if st.button("Delete", key=f"{key_prefix}_del_{e['id']}"):
                lib.delete_entry(e["id"])
                st.rerun()


# ---------- Always-visible open follow-ups ----------
overdue = lib.overdue_followups()
if overdue:
    st.subheader(f"⚠️ Overdue ({len(overdue)})")
    for f in overdue:
        render_card(f, "overdue")
    st.divider()

tab_week, tab_add, tab_browse = st.tabs(["📆 This week", "➕ Add entry", "🔍 Browse & search"])

# ---------- This week ----------
with tab_week:
    week_start, week_end = lib.week_range()
    st.caption(f"{week_start} to {week_end}")

    show_types = st.multiselect(
        "Show", ENTRY_TYPES, default=ENTRY_TYPES,
        format_func=lambda t: TYPE_STYLE[t]["label"],
        key="week_type_filter",
    )

    week_entries = lib.get_entries(date_from=week_start, date_to=week_end,
                                    entry_types=show_types or ENTRY_TYPES)

    # Also surface still-open follow-ups from before this week, so nothing
    # drops off the radar just because the week rolled over.
    week_entry_ids = {e["id"] for e in week_entries}
    older_open_followups = [
        f for f in lib.open_followups()
        if f["entry_date"] < week_start and f["id"] not in week_entry_ids
    ]

    if not week_entries and not older_open_followups:
        st.info("Nothing logged this week yet.")
    else:
        for e in week_entries:
            render_card(e, "week")
        if older_open_followups and "followup" in (show_types or ENTRY_TYPES):
            st.markdown("**Still open from earlier**")
            for f in older_open_followups:
                render_card(f, "weekold")

# ---------- Add entry ----------
with tab_add:
    c1, c2 = st.columns([1, 2])
    with c1:
        entry_date = st.date_input("Date", value=date.today())
        entry_type = st.radio(
            "Type", ENTRY_TYPES, format_func=lambda t: TYPE_STYLE[t]["label"],
        )
        due_date = None
        if entry_type == "followup":
            due_date = st.date_input("Follow up by", value=None)
    with c2:
        title = st.text_input("Title", placeholder="e.g. Call with Dr. Khan about reagent order")
        body = st.text_area("Details", height=150,
                             placeholder="What happened, what was discussed, next steps...")

    if st.button("Save entry", type="primary"):
        if not body.strip():
            st.warning("Add some detail before saving.")
        else:
            lib.add_entry(entry_date.isoformat(), entry_type, title.strip(), body.strip(),
                          due_date.isoformat() if due_date else None)
            st.success("Saved.")
            st.rerun()

# ---------- Browse & search ----------
with tab_browse:
    if "notes_cal_year" not in st.session_state:
        today = date.today()
        st.session_state.notes_cal_year = today.year
        st.session_state.notes_cal_month = today.month

    c1, c2, c3, c4 = st.columns([1, 2, 1, 3])
    with c1:
        if st.button("◀"):
            m = st.session_state.notes_cal_month - 1
            y = st.session_state.notes_cal_year
            if m == 0:
                m, y = 12, y - 1
            st.session_state.notes_cal_month, st.session_state.notes_cal_year = m, y
    with c2:
        st.markdown(f"### {calendar.month_name[st.session_state.notes_cal_month]} {st.session_state.notes_cal_year}")
    with c3:
        if st.button("▶"):
            m = st.session_state.notes_cal_month + 1
            y = st.session_state.notes_cal_year
            if m == 13:
                m, y = 1, y + 1
            st.session_state.notes_cal_month, st.session_state.notes_cal_year = m, y

    search = st.text_input("Search all entries", placeholder="Search notes, correspondence & follow-ups…")
    type_filter = st.multiselect("Filter by type", ENTRY_TYPES, default=ENTRY_TYPES,
                                  format_func=lambda t: TYPE_STYLE[t]["label"], key="browse_type_filter")

    cal_days = lib.entries_calendar_days(st.session_state.notes_cal_year, st.session_state.notes_cal_month)
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(st.session_state.notes_cal_year, st.session_state.notes_cal_month)

    if "notes_selected_date" not in st.session_state:
        st.session_state.notes_selected_date = date.today().isoformat()

    st.write("")
    st.caption("🔵 note · 🟣 correspondence · 🟠 follow-up")
    header_cols = st.columns(7)
    for hc, dname in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        hc.markdown(f"**{dname}**")

    for week in weeks:
        cols = st.columns(7)
        for col, day_num in zip(cols, week):
            if day_num == 0:
                col.write("")
                continue
            d_iso = date(st.session_state.notes_cal_year, st.session_state.notes_cal_month, day_num).isoformat()
            counts = cal_days.get(d_iso, {})
            dots = "".join(
                {"note": "🔵", "correspondence": "🟣", "followup": "🟠"}[t]
                for t in ENTRY_TYPES if counts.get(t)
            )
            label = f"{day_num}\n{dots}" if dots else str(day_num)
            if col.button(label, key=f"cal_{d_iso}", width="stretch"):
                st.session_state.notes_selected_date = d_iso

    st.divider()

    if search or set(type_filter) != set(ENTRY_TYPES):
        results = lib.get_entries(search=search or None, entry_types=type_filter or ENTRY_TYPES)
        st.markdown(f"**{len(results)} result(s)**")
        for e in results:
            render_card(e, "search")
    else:
        st.markdown(f"**Entries for {st.session_state.notes_selected_date}**")
        day_entries = lib.get_entries(date_from=st.session_state.notes_selected_date,
                                       date_to=st.session_state.notes_selected_date)
        if not day_entries:
            st.caption("Nothing logged for this date.")
        for e in day_entries:
            render_card(e, "day")
