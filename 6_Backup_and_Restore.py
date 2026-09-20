"""
This page exists because of a real, lived problem: on Streamlit Cloud's
free tier, the SQLite file resets on every redeploy — and a redeploy
happens every time you push a fix to GitHub. Two schema-changing fixes in
one afternoon meant two accidental full resets. This page doesn't stop
that from being possible, but it makes sure it's never a surprise, and
never total: back up before you touch code, restore in one click after.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import os

from db import init_db, DB_PATH
import lib

st.set_page_config(page_title="Backup & Restore — LabPilot", page_icon="💾", layout="wide")
init_db()

st.title("💾 Backup & Restore")
st.caption("Your data lives in one local file that does NOT survive a redeploy on Streamlit "
           "Cloud's free tier. Download a backup before making any change to the code, and "
           "you can restore it in one click afterward.")

days = lib.days_since_backup()
last = lib.last_backup()

if days is None:
    st.error("⚠️ No backup has ever been taken. If this app redeploys right now, everything "
             "you've entered is gone for good. Download one below before doing anything else.")
elif days == 0:
    st.success(f"✅ Backed up today, via {last['method']}.")
elif days <= 7:
    st.info(f"Last backup was {days} day(s) ago ({last['method']}).")
else:
    st.warning(f"⚠️ Last backup was {days} days ago ({last['method']}). "
               "That's a lot to lose — consider backing up again now.")

st.divider()

tab_backup, tab_restore = st.tabs(["⬇️ Back up", "⬆️ Restore"])

# ---------- Backup ----------
with tab_backup:
    counts = lib.database_row_counts()
    st.markdown("**Currently in the database**")
    st.dataframe(pd.DataFrame([counts]).T.rename(columns={0: "rows"}), width="stretch")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Database file (.db)")
        st.caption("Exact, perfect copy — the fastest way to restore everything precisely "
                   "as it was.")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            clicked = st.download_button(
                "Download database file", data=db_bytes,
                file_name=f"labpilot_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.db",
                mime="application/octet-stream",
            )
            if clicked:
                lib.record_backup("sqlite file")
                st.success("Backup downloaded and logged.")
                st.rerun()
        else:
            st.caption("No database file yet.")

    with c2:
        st.markdown("#### Excel workbook (all tables)")
        st.caption("Human-readable — open it yourself to double-check anything, or hand it to "
                   "someone else without needing this app.")
        if st.button("Prepare Excel backup"):
            from db import get_conn
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                with get_conn() as conn:
                    for table in ["schedule", "inventory", "experiments", "experiment_items",
                                  "experiment_history", "tracker_log", "tracker_items", "entries"]:
                        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                        df.to_excel(writer, sheet_name=table[:31], index=False)
            st.session_state["excel_backup_bytes"] = buffer.getvalue()

        if "excel_backup_bytes" in st.session_state:
            clicked_xl = st.download_button(
                "Download Excel backup", data=st.session_state["excel_backup_bytes"],
                file_name=f"labpilot_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if clicked_xl:
                lib.record_backup("excel export")
                st.success("Backup downloaded and logged.")
                del st.session_state["excel_backup_bytes"]
                st.rerun()

# ---------- Restore ----------
with tab_restore:
    st.warning("Restoring **overwrites everything currently in the app** — the whole "
               "database is replaced. Only proceed if you're sure this is what you want.")
    up = st.file_uploader("Upload a previously downloaded .db backup file", type=["db"])

    if up:
        st.markdown(f"File selected: **{up.name}** ({up.size:,} bytes)")
        confirm_text = st.text_input(
            'Type RESTORE (all capitals) to confirm you want to overwrite everything',
        )
        if st.button("Restore now", type="primary", disabled=(confirm_text != "RESTORE")):
            with open(DB_PATH, "wb") as f:
                f.write(up.getbuffer())
            st.success("Database restored. Reloading...")
            st.rerun()

    st.divider()
    st.caption("Only .db files created by this app's own backup can be restored this way. "
               "An Excel backup is for reading/reference — restoring from Excel would need "
               "the Import Data page's importers instead, table by table.")
