import streamlit as st
import calendar
from datetime import date

from db import init_db
import lib

st.set_page_config(page_title="Notes — LabPilot", page_icon="📝", layout="wide")
init_db()

st.title("📝 Notes & Correspondence")
st.caption("Daily notes and a record of correspondence — who you contacted, what was said, "
           "and when. Everything here is searchable and dated.")

tab_add, tab_browse = st.tabs(["Add entry", "Browse & search"])

with tab_add:
    c1, c2 = st.columns([1, 2])
    with c1:
        entry_date = st.date_input("Date", value=date.today())
        entry_type = st.radio("Type", ["note", "correspondence"], horizontal=True)
    with c2:
        title = st.text_input("Title", placeholder="e.g. Call with Dr. Khan about reagent order")
        body = st.text_area("Details", height=150,
                             placeholder="What happened, what was discussed, next steps...")

    if st.button("Save entry", type="primary"):
        if not body.strip():
            st.warning("Add some detail before saving.")
        else:
            lib.add_note(entry_date.isoformat(), entry_type, title.strip(), body.strip())
            st.success("Saved.")
            st.rerun()

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

    with c4:
        search = st.text_input("Search all notes", key="notes_search", label_visibility="collapsed",
                                placeholder="Search all notes & correspondence…")
        type_filter = st.selectbox("Type", ["All", "note", "correspondence"], label_visibility="collapsed")

    note_days = lib.notes_calendar_days(st.session_state.notes_cal_year, st.session_state.notes_cal_month)
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(st.session_state.notes_cal_year, st.session_state.notes_cal_month)

    if "notes_selected_date" not in st.session_state:
        st.session_state.notes_selected_date = date.today().isoformat()

    st.write("")
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
            has_note = d_iso in note_days
            label = f"● {day_num}" if has_note else str(day_num)
            if col.button(label, key=f"cal_{d_iso}", width='stretch'):
                st.session_state.notes_selected_date = d_iso

    st.divider()

    if search or type_filter != "All":
        results = lib.get_notes(search=search or None, note_type=type_filter)
        st.markdown(f"**{len(results)} result(s)**")
        for n in results:
            with st.expander(f"{n['note_date']} · {n['note_type']} · {n['title'] or '(untitled)'}"):
                st.write(n["body"])
                if st.button("Delete", key=f"delsearch_{n['id']}"):
                    lib.delete_note(n["id"])
                    st.rerun()
    else:
        st.markdown(f"**Notes for {st.session_state.notes_selected_date}**")
        day_notes = lib.get_notes(date_from=st.session_state.notes_selected_date,
                                   date_to=st.session_state.notes_selected_date)
        if not day_notes:
            st.caption("Nothing logged for this date.")
        for n in day_notes:
            with st.expander(f"{n['note_type']} · {n['title'] or '(untitled)'}"):
                st.write(n["body"])
                if st.button("Delete", key=f"delday_{n['id']}"):
                    lib.delete_note(n["id"])
                    st.rerun()
