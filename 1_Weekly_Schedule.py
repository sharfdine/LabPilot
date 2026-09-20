import streamlit as st
import pandas as pd

from db import init_db, DAYS, ROOMS, SLOTS, slot_label
import lib

st.set_page_config(page_title="Weekly Schedule — LabPilot", page_icon="📅", layout="wide")
init_db()

st.title("📅 Weekly Schedule")
st.caption("The master timetable. Every other page (Experiments, Tracker) reads from this — "
           "edit it here once and everything downstream follows.")

room_tabs = st.tabs(ROOMS)

for tab, r in zip(room_tabs, ROOMS):
    with tab:
        rows = []
        for day in DAYS:
            for start, end, label in SLOTS:
                slot = lib.get_slot(day, r, start)
                rows.append({
                    "Day": day,
                    "Time": label,
                    "Course": slot["course"] if slot else "",
                    "Section": slot["section"] if slot else "",
                    "Instructor": slot["instructor"] if slot else "",
                    "_start": start,
                    "_end": end,
                })
        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df.drop(columns=["_start", "_end"]),
            key=f"editor_{r}",
            width="stretch",
            hide_index=True,
            disabled=["Day", "Time"],
            column_config={
                "Course": st.column_config.TextColumn(help="Leave blank for a free slot"),
            },
        )

        if st.button(f"Save changes — {r}", key=f"save_{r}"):
            for i, row in edited.iterrows():
                orig = df.iloc[i]
                course = row["Course"].strip() or None
                section = row["Section"].strip() or None
                instructor = row["Instructor"].strip() or None
                lib.upsert_slot(orig["Day"], r, orig["_start"], orig["_end"], course, section, instructor)
            st.success(f"{r} schedule saved.")
            st.rerun()

st.divider()
st.caption("Adding a brand-new course here (a new course/instructor pair) will automatically "
           "create a card for it on the Experiments page — nothing extra to set up.")
