import streamlit as st

from db import init_db, ROOMS
import lib

st.set_page_config(page_title="Experiments — LabPilot", page_icon="🧪", layout="wide")
init_db()

st.title("🧪 Experiments")
st.caption("One card per course. Set this week's experiment once and it applies to every "
           "session of that course, no matter how many days it recurs on.")

groups = lib.course_groups()
if not groups:
    st.info("No courses on the schedule yet — add some on the Weekly Schedule page.")
    st.stop()

sorted_keys = sorted(groups.keys(), key=lambda k: k[0])

for course, instructor in sorted_keys:
    g = groups[(course, instructor)]
    exp = lib.get_experiment(course, instructor) or {"experiment_name": "", "items": [], "history": []}

    occ_str = " · ".join(
        f"{o['day'][:3]} {o['slot_start']} ({o['room']})" for o in g["occurrences"]
    )

    with st.expander(f"**{course}** — {instructor}", expanded=False):
        st.caption(occ_str)

        new_name = st.text_input(
            "This week's experiment",
            value=exp["experiment_name"] or "",
            key=f"expname_{course}_{instructor}",
            placeholder="e.g. Aqueous extraction of turmeric",
        )
        if st.button("Save experiment name", key=f"savename_{course}_{instructor}"):
            lib.set_experiment_name(course, instructor, g["room"], new_name.strip())
            st.success("Saved.")
            st.rerun()

        if exp["history"]:
            with st.popover(f"Past experiments ({len(exp['history'])})"):
                for h in exp["history"]:
                    st.markdown(f"- **{h['changed_date'][:10]}** — {h['experiment_name']}")

        st.markdown("**Needed items** (chemicals & lab ware — quantity optional)")

        if exp["items"]:
            for item in exp["items"]:
                c1, c2 = st.columns([5, 1])
                with c1:
                    qty_str = f" — {item['planned_qty']} {item['unit']}" if item["planned_qty"] else ""
                    room_tag = f" *({item['room']})*" if item.get("room") else ""
                    st.markdown(f"- {item['item_type'].title()}: **{item['item_name']}**{qty_str} "
                                f"· {item['location']}{room_tag}")
                with c2:
                    if st.button("Remove", key=f"rmitem_{item['id']}"):
                        lib.remove_experiment_item(item["id"])
                        st.rerun()
        else:
            st.caption("Nothing added yet.")

        st.markdown("**Add an item** — searches both labs' stock")
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            item_type = st.radio("Type", ["chemical", "labware"], key=f"type_{course}_{instructor}",
                                  horizontal=True, label_visibility="collapsed")
        query = st.text_input("Search item name", key=f"search_{course}_{instructor}",
                               placeholder="Start typing a chemical or lab ware name…")
        matches = lib.search_inventory(query, item_type=item_type) if query else []

        if matches:
            options = {f"{m['item_name']} — {m['room']} ({m['location']})": m for m in matches}
            choice = st.selectbox("Pick the exact stock entry", list(options.keys()),
                                   key=f"choice_{course}_{instructor}")
            picked = options[choice]
            qty = st.text_input("Quantity needed (optional)", key=f"qty_{course}_{instructor}")
            if st.button("Add item", key=f"additem_{course}_{instructor}"):
                try:
                    qty_val = float(qty) if qty.strip() else None
                except ValueError:
                    qty_val = None
                lib.add_experiment_item(
                    course, instructor, g["room"],
                    picked["item_name"], picked["item_type"], picked["unit"],
                    picked["location"], picked["room"], qty_val,
                )
                st.rerun()
        elif query:
            st.caption("No matches in either lab's inventory. Check spelling, or add it via "
                       "the Import Data page if it's genuinely new stock.")
