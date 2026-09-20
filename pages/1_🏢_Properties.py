import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id

def get_account_setting(key, account_id):
    a = get_account(account_id)
    return (a or {}).get(key, "ZAR" if key == "currency" else "")
from utils.logic import (
    add_property, list_properties, update_property, delete_property,
    add_unit, list_units, get_unit, update_unit, delete_unit,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Properties", page_icon="🏢", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
currency = get_account_setting("currency", account_id)

page_header("Properties & Units", icon="🏢")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs(["Properties", "Units"])

with tab1:
    section_label("Add a property")
    with st.form("add_property_form", clear_on_submit=True):
        name = st.text_input("Property name*")
        address = st.text_input("Address")
        submitted = st.form_submit_button("Add property")
        if submitted:
            if not require_active_subscription():
                pass
            elif not name.strip():
                st.error("Property name is required.")
            else:
                add_property(name.strip(), address.strip(), account_id=account_id)
                st.success(f"Added property '{name}'.")
                st.rerun()

    section_label("Existing properties")
    properties = list_properties(account_id=account_id)
    if not properties:
        empty_state("No properties yet. Add one above to get started.", icon="🏘️")
    else:
        for p in properties:
            with st.expander(f"{p['name']} — {p['address'] or 'no address'}"):
                units_here = list_units(p["id"], account_id=account_id)
                st.write(f"{len(units_here)} unit(s)")

                edit_key = f"editing_prop_{p['id']}"
                if not st.session_state.get(edit_key):
                    col1, col2 = st.columns(2)
                    if col1.button("Edit", key=f"edit_btn_prop_{p['id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()
                    if col2.button("Delete property", key=f"del_prop_{p['id']}"):
                        if require_active_subscription():
                            delete_property(p["id"])
                            st.warning(f"Deleted property '{p['name']}' and its units.")
                            st.rerun()
                else:
                    with st.form(f"edit_prop_form_{p['id']}"):
                        new_name = st.text_input("Property name", value=p["name"])
                        new_address = st.text_input("Address", value=p["address"] or "")
                        col1, col2 = st.columns(2)
                        save = col1.form_submit_button("Save changes")
                        cancel = col2.form_submit_button("Cancel")
                        if save:
                            if not require_active_subscription():
                                pass
                            elif not new_name.strip():
                                st.error("Property name is required.")
                            else:
                                update_property(p["id"], new_name.strip(), new_address.strip())
                                st.session_state[edit_key] = False
                                st.success("Property updated.")
                                st.rerun()
                        if cancel:
                            st.session_state[edit_key] = False
                            st.rerun()

with tab2:
    properties = list_properties(account_id=account_id)
    if not properties:
        empty_state("Add a property first before creating units.", icon="🏢")
    else:
        section_label("Add a unit")
        with st.form("add_unit_form", clear_on_submit=True):
            prop_options = {p["name"]: p["id"] for p in properties}
            prop_name = st.selectbox("Property*", list(prop_options.keys()))
            unit_name = st.text_input("Unit name/number* (e.g. 'A1', 'House 3')")
            monthly_rent = st.number_input(f"Monthly rent ({currency})*", min_value=0.0, step=10000.0)
            water_rate = st.number_input(f"Water rate per month ({currency})", min_value=0.0, step=1000.0)
            submitted = st.form_submit_button("Add unit")
            if submitted:
                if not require_active_subscription():
                    pass
                elif not unit_name.strip():
                    st.error("Unit name is required.")
                else:
                    add_unit(prop_options[prop_name], unit_name.strip(), monthly_rent, water_rate)
                    st.success(f"Added unit '{unit_name}'.")
                    st.rerun()

        section_label("All units")
        units = list_units(account_id=account_id)
        if not units:
            empty_state("No units yet. Add one above.", icon="🔑")
        else:
            import pandas as pd
            df = pd.DataFrame([{
                "Property": u["property_name"],
                "Unit": u["unit_name"],
                f"Rent ({currency})": f"{u['monthly_rent']:,.0f}",
                f"Water rate ({currency})": f"{u['water_rate']:,.0f}",
                "Status": u["status"],
            } for u in units])
            st.dataframe(df, use_container_width=True, hide_index=True)

            section_label("Edit a unit")
            unit_options = {f"{u['property_name']} — {u['unit_name']}": u["id"] for u in units}
            unit_to_edit_label = st.selectbox("Select unit to edit", list(unit_options.keys()), key="edit_unit_select")
            unit_to_edit = get_unit(unit_options[unit_to_edit_label])

            with st.form("edit_unit_form"):
                new_unit_name = st.text_input("Unit name/number", value=unit_to_edit["unit_name"])
                new_rent = st.number_input(f"Monthly rent ({currency})", min_value=0.0,
                                            value=float(unit_to_edit["monthly_rent"]), step=10000.0)
                new_water = st.number_input(f"Water rate ({currency})", min_value=0.0,
                                             value=float(unit_to_edit["water_rate"]), step=1000.0)
                save_unit = st.form_submit_button("Save changes")
                if save_unit:
                    if not require_active_subscription():
                        pass
                    elif not new_unit_name.strip():
                        st.error("Unit name is required.")
                    else:
                        update_unit(unit_to_edit["id"], new_unit_name.strip(), new_rent, new_water)
                        st.success("Unit updated. Note: this changes the rate going forward — "
                                    "past rent charges already generated are not retroactively changed.")
                        st.rerun()

            section_label("Delete a unit")
            unit_to_delete_label = st.selectbox("Select unit to delete", list(unit_options.keys()), key="delete_unit_select")
            if st.button("Delete selected unit"):
                if require_active_subscription():
                    delete_unit(unit_options[unit_to_delete_label])
                    st.warning("Unit deleted.")
                    st.rerun()
