import streamlit as st
from datetime import date

from db import init_db, slot_label
import lib

st.set_page_config(page_title="Lab Tracker — LabPilot", page_icon="📋", layout="wide")
init_db()

st.title("📋 Lab Tracker")
st.caption("What actually happened, and what was actually used. Log same-day, or catch up on "
           "the whole week in one sitting — nothing here expects real-time entry.")

tab_pending, tab_new, tab_history = st.tabs(["Awaiting confirmation", "Log a session manually", "Full history"])

# ---------- Awaiting confirmation ----------
with tab_pending:
    pending = lib.pending_confirmations(days_back=14)
    if not pending:
        st.success("Nothing waiting — you're caught up.")
    else:
        st.caption(f"{len(pending)} finished session(s) with no log entry yet, going back two weeks.")
        for p in pending:
            with st.expander(f"{p['date']} ({p['day']}) · {p['room']} · {p['slot_label']} — "
                              f"{p['course']} ({p['section']})"):
                st.caption(f"Instructor: {p['instructor']}")
                exp_name = st.text_input("Experiment performed", value=p["experiment_name"],
                                          key=f"pend_exp_{p['date']}_{p['room']}_{p['slot_start']}")

                st.markdown("**Actual quantities used**")
                item_inputs = []
                for item in p["planned_items"]:
                    key = f"pend_qty_{p['date']}_{p['room']}_{p['slot_start']}_{item['id']}"
                    qty = st.text_input(
                        f"{item['item_name']} ({item['unit']}, {item['location']})",
                        key=key, placeholder="qty used, optional",
                    )
                    item_inputs.append((item, qty))

                notes = st.text_area("Notes (yield, deviations, issues)",
                                      key=f"pend_notes_{p['date']}_{p['room']}_{p['slot_start']}")

                if st.button("Confirm & log", key=f"pend_confirm_{p['date']}_{p['room']}_{p['slot_start']}"):
                    items = []
                    for item, qty in item_inputs:
                        try:
                            qty_val = float(qty) if qty.strip() else None
                        except ValueError:
                            qty_val = None
                        items.append({
                            "item_name": item["item_name"], "item_type": item["item_type"],
                            "unit": item["unit"], "location": item["location"], "qty_used": qty_val,
                        })
                    lib.save_tracker_entry(
                        p["date"], p["day"], p["room"], p["slot_start"], p["slot_end"],
                        p["course"], p["section"], p["instructor"],
                        exp_name.strip() or p["course"], notes.strip(), items,
                    )
                    st.success("Logged.")
                    st.rerun()

# ---------- Manual entry ----------
with tab_new:
    st.caption("For anything the auto-detection missed, or a session from further back.")
    groups = lib.course_groups()
    if not groups:
        st.info("No courses on the schedule yet.")
    else:
        keys = sorted(groups.keys(), key=lambda k: k[0])
        labels = [f"{c} — {i}" for c, i in keys]
        choice = st.selectbox("Course", labels)
        course, instructor = keys[labels.index(choice)]
        g = groups[(course, instructor)]
        exp = lib.get_experiment(course, instructor)

        log_date = st.date_input("Date performed", value=date.today())
        exp_name = st.text_input("Experiment performed",
                                  value=(exp["experiment_name"] if exp else "") or "")

        st.markdown("**Items used**")
        planned = exp["items"] if exp else []
        item_inputs = []
        for item in planned:
            qty = st.text_input(f"{item['item_name']} ({item['unit']}, {item['location']})",
                                 key=f"manual_qty_{item['id']}", placeholder="qty used, optional")
            item_inputs.append((item, qty))

        with st.expander("Add an extra item not on the planned list"):
            item_type = st.radio("Type", ["chemical", "labware"], horizontal=True, key="manual_extra_type")
            query = st.text_input("Search", key="manual_extra_search")
            extra_item = None
            extra_qty = ""
            if query:
                matches = lib.search_inventory(query, item_type=item_type)
                if matches:
                    options = {f"{m['item_name']} — {m['room']} ({m['location']})": m for m in matches}
                    pick = st.selectbox("Match", list(options.keys()), key="manual_extra_pick")
                    extra_item = options[pick]
                    extra_qty = st.text_input("Qty used (optional)", key="manual_extra_qty")

        notes = st.text_area("Notes", key="manual_notes")

        if st.button("Save log entry", type="primary"):
            items = []
            for item, qty in item_inputs:
                try:
                    qty_val = float(qty) if qty.strip() else None
                except ValueError:
                    qty_val = None
                items.append({"item_name": item["item_name"], "item_type": item["item_type"],
                               "unit": item["unit"], "location": item["location"], "qty_used": qty_val})
            if extra_item:
                try:
                    extra_qty_val = float(extra_qty) if extra_qty.strip() else None
                except ValueError:
                    extra_qty_val = None
                items.append({"item_name": extra_item["item_name"], "item_type": extra_item["item_type"],
                               "unit": extra_item["unit"], "location": extra_item["location"],
                               "qty_used": extra_qty_val})

            day_name = log_date.strftime("%A")
            occ = next((o for o in g["occurrences"]), {"slot_start": "", "slot_end": ""})
            lib.save_tracker_entry(
                log_date.isoformat(), day_name, g["room"], occ["slot_start"], occ["slot_end"],
                course, None, instructor, exp_name.strip() or course, notes.strip(), items,
            )
            st.success("Logged.")
            st.rerun()

# ---------- History ----------
with tab_history:
    c1, c2, c3 = st.columns(3)
    search = c1.text_input("Search course, instructor, experiment, or notes")
    date_from = c2.date_input("From", value=None, key="hist_from")
    date_to = c3.date_input("To", value=None, key="hist_to")

    entries = lib.get_tracker_log(
        search=search or None,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )
    st.caption(f"{len(entries)} entr{'y' if len(entries)==1 else 'ies'}")

    for e in entries:
        with st.expander(f"{e['log_date']} · {e['room']} · {e['course']} — {e['experiment_name']}"):
            st.caption(f"{e['instructor']} · {e['day'] or ''} {slot_label(e['slot_start'], e['slot_end']) if e['slot_start'] else ''}")
            if e["items"]:
                for it in e["items"]:
                    qty = f"{it['qty_used']} {it['unit']}" if it["qty_used"] else "qty not recorded"
                    st.markdown(f"- {it['item_name']}: {qty} ({it['location']})")
            if e["notes"]:
                st.markdown(f"*{e['notes']}*")
            if st.button("Delete entry", key=f"del_{e['id']}"):
                lib.delete_tracker_entry(e["id"])
                st.rerun()
