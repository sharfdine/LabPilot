"""
This page is what makes the whole system self-updating: instead of anyone
retyping a schedule or inventory sheet by hand, you upload the file FCCU
(or the lab store) actually issues, and it's parsed directly into the
database.

Two parsers are built in, matching the two file formats seen so far:
  1. The multi-block "Classes / Lab" weekly schedule export
     (e.g. PharmD_Labs_Schedule-FL26.xlsx)
  2. The chemical stock / expiry sheets, one tab per room
     (e.g. Expiry_date_file.xlsx, sheets named like S135CC / S138CC)

A generic CSV importer is also included for anything else.
"""

import streamlit as st
import pandas as pd
import openpyxl
import re

from db import init_db, DAYS, ROOMS
import lib

st.set_page_config(page_title="Import Data — LabPilot", page_icon="📥", layout="wide")
init_db()

st.title("📥 Import Data")
st.caption("Feed the system a new file instead of retyping it. Nothing here overwrites "
           "silently — you review the parsed result before it's saved.")

tab_schedule, tab_inventory, tab_csv = st.tabs(
    ["Weekly schedule (Classes/Lab format)", "Chemical/lab ware stock", "Generic CSV"]
)

DAY_MAP = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}


# ---------- Schedule import ----------
with tab_schedule:
    st.markdown("For files shaped like **PharmD_Labs_Schedule-FL26.xlsx** — a sheet per term, "
                "with a 'Classes' header row and a 'Lab' header row, then repeating day blocks "
                "of room rows (135B, 138B, and lecture sections).")
    up = st.file_uploader("Upload the schedule workbook", type=["xlsx"], key="sched_upload")

    if up:
        wb = openpyxl.load_workbook(up, data_only=True)
        sheet_name = st.selectbox("Which sheet is this term's schedule?", wb.sheetnames)
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(min_row=1, max_row=60, values_only=True))

        classes_header = rows[1]
        lab_header = rows[2]
        data_rows = rows[3:]

        parsed = {}
        current_day = None
        i = 0
        while i < len(data_rows):
            row = data_rows[i]
            if row[0] is not None:
                current_day = DAY_MAP.get(row[0], row[0])
                parsed[current_day] = {}
            if current_day is None:
                i += 1
                continue
            room = row[1]
            if room is None:
                i += 1
                continue
            entries = {}
            for col in range(2, len(row)):
                val = row[col]
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    continue
                if room in ROOMS and col < len(lab_header) and lab_header[col]:
                    label = lab_header[col]
                elif col < len(classes_header) and classes_header[col]:
                    label = classes_header[col]
                else:
                    continue
                text = re.sub(r"\s+", " ", val).strip() if isinstance(val, str) else val
                entries[label] = text
            parsed[current_day][room] = entries
            i += 1

        st.markdown("**Preview — 135B / 138B only** (the two lab rooms this system tracks)")
        preview_rows = []
        for day in DAYS:
            for room in ROOMS:
                for label, text in parsed.get(day, {}).get(room, {}).items():
                    preview_rows.append({"Day": day, "Room": room, "Period": label, "Content": text})
        preview_df = pd.DataFrame(preview_rows)
        st.dataframe(preview_df, width='stretch', hide_index=True)

        st.warning("This importer only recognizes the two standard 3-hour block periods "
                   "(11:00-14:00-ish and 14:00-17:00-ish) as genuine lab sessions — shorter "
                   "lecture-style periods shown above are for your reference only.")

        st.info("Automatic mapping into the Weekly Schedule grid depends on exact period "
                "labels matching across terms, which varies file to file — for reliability, "
                "please apply the rows shown above manually on the Weekly Schedule page for "
                "now. Full auto-mapping is a good next enhancement once a few more terms' "
                "files establish a consistent pattern.")


# ---------- Inventory import ----------
with tab_inventory:
    st.markdown("For files shaped like **Expiry_date_file.xlsx** — one sheet per room "
                "(e.g. `S135CC`, `S138CC`), with columns for item name, unit, location, and stock.")
    up2 = st.file_uploader("Upload the inventory workbook", type=["xlsx"], key="inv_upload")

    if up2:
        wb2 = openpyxl.load_workbook(up2, data_only=True)
        sheet_name2 = st.selectbox("Which sheet?", wb2.sheetnames, key="inv_sheet")
        room_guess = "135B" if "135" in sheet_name2 else ("138B" if "138" in sheet_name2 else ROOMS[0])
        room_pick = st.selectbox("Which room is this stock for?", ROOMS,
                                  index=ROOMS.index(room_guess) if room_guess in ROOMS else 0)
        item_type_pick = st.radio("Item type", ["chemical", "labware"], horizontal=True)

        ws2 = wb2[sheet_name2]
        data = list(ws2.iter_rows(values_only=True))
        header = data[0]
        st.caption(f"Detected columns: {header}")

        col_map = {}
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            name_col = st.number_input("Item name column #", min_value=0, max_value=len(header)-1, value=1)
        with c2:
            unit_col = st.number_input("Unit column #", min_value=0, max_value=len(header)-1, value=2)
        with c3:
            loc_col = st.number_input("Location column #", min_value=0, max_value=len(header)-1, value=3)
        with c4:
            qty_col = st.number_input("Stock qty column #", min_value=0, max_value=len(header)-1, value=4)

        preview = []
        for r in data[1:]:
            name = r[name_col] if name_col < len(r) else None
            if not name or str(name).strip() == "":
                continue
            preview.append({
                "item_name": str(name).strip(),
                "unit": str(r[unit_col]).strip() if unit_col < len(r) and r[unit_col] else "",
                "location": str(r[loc_col]).strip() if loc_col < len(r) and r[loc_col] else "",
                "stock_qty": r[qty_col] if qty_col < len(r) else None,
            })

        st.markdown(f"**Preview — {len(preview)} item(s)**")
        st.dataframe(pd.DataFrame(preview).head(20), width='stretch', hide_index=True)

        if st.button("Import into inventory", type="primary"):
            from db import get_conn
            with get_conn() as conn:
                count = 0
                for p in preview:
                    try:
                        qty = float(p["stock_qty"]) if p["stock_qty"] not in (None, "") else None
                    except (ValueError, TypeError):
                        qty = None
                    conn.execute(
                        "INSERT INTO inventory (item_name, item_type, unit, location, room, stock_qty) "
                        "VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(item_name, room, location, item_type) DO UPDATE SET stock_qty=excluded.stock_qty",
                        (p["item_name"], item_type_pick, p["unit"], p["location"], room_pick, qty),
                    )
                    count += 1
            st.success(f"Imported/updated {count} item(s) for {room_pick}.")


# ---------- Generic CSV ----------
with tab_csv:
    st.markdown("For a plain CSV — schedule columns: `day, room, slot_start, course, section, "
                "instructor`. Inventory columns: `item_name, item_type, unit, location, room, "
                "stock_qty`.")
    which = st.radio("What is this CSV?", ["Schedule", "Inventory"], horizontal=True)
    up3 = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload")
    if up3:
        df = pd.read_csv(up3)
        st.dataframe(df, width='stretch', hide_index=True)
        if which == "Schedule" and st.button("Import schedule rows", type="primary"):
            n = 0
            for _, r in df.iterrows():
                start = str(r["slot_start"])
                end = "14:00" if start.startswith("11") else "17:00"
                lib.upsert_slot(r["day"], r["room"], start, end,
                                 r.get("course") or None, r.get("section") or None,
                                 r.get("instructor") or None)
                n += 1
            st.success(f"Updated {n} schedule row(s).")
        if which == "Inventory" and st.button("Import inventory rows", type="primary"):
            from db import get_conn
            with get_conn() as conn:
                n = 0
                for _, r in df.iterrows():
                    conn.execute(
                        "INSERT INTO inventory (item_name, item_type, unit, location, room, stock_qty) "
                        "VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(item_name, room, location, item_type) DO UPDATE SET stock_qty=excluded.stock_qty",
                        (r["item_name"], r.get("item_type", "chemical"), r.get("unit", ""),
                         r.get("location", ""), r["room"], r.get("stock_qty")),
                    )
                    n += 1
            st.success(f"Imported/updated {n} item(s).")
