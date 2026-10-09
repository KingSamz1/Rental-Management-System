import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t

def get_account_setting(key, account_id):
    a = get_account(account_id)
    return (a or {}).get(key, "UGX" if key == "currency" else "")
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

page_header(t("Properties & Units"), icon="🏢")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs([t("Properties"), t("Units")])

with tab1:
    section_label(t("Add a property"))
    with st.form("add_property_form", clear_on_submit=True):
        name = st.text_input(t("Property name*"))
        address = st.text_input(t("Address"))
        submitted = st.form_submit_button(t("Add property"))
        if submitted:
            if not require_active_subscription():
                pass
            elif not name.strip():
                st.error(t("Property name is required."))
            else:
                add_property(name.strip(), address.strip(), account_id=account_id)
                st.success(t("Added property") + f" '{name}'.")
                st.rerun()

    section_label(t("Existing properties"))
    properties = list_properties(account_id=account_id)
    if not properties:
        empty_state(t("No properties yet. Add one above to get started."), icon="🏘️")
    else:
        for p in properties:
            with st.expander(f"{p['name']} — {p['address'] or t('no address')}"):
                units_here = list_units(p["id"], account_id=account_id)
                st.write(f"{len(units_here)} {t('unit(s)')}")

                edit_key = f"editing_prop_{p['id']}"
                if not st.session_state.get(edit_key):
                    col1, col2 = st.columns(2)
                    if col1.button(t("Edit"), key=f"edit_btn_prop_{p['id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()
                    if col2.button(t("Delete property"), key=f"del_prop_{p['id']}"):
                        if require_active_subscription():
                            delete_property(p["id"])
                            st.warning(t("Deleted property") + f" '{p['name']}'.")
                            st.rerun()
                else:
                    with st.form(f"edit_prop_form_{p['id']}"):
                        new_name = st.text_input(t("Property name"), value=p["name"])
                        new_address = st.text_input(t("Address"), value=p["address"] or "")
                        col1, col2 = st.columns(2)
                        save = col1.form_submit_button(t("Save changes"))
                        cancel = col2.form_submit_button(t("Cancel"))
                        if save:
                            if not require_active_subscription():
                                pass
                            elif not new_name.strip():
                                st.error(t("Property name is required."))
                            else:
                                update_property(p["id"], new_name.strip(), new_address.strip())
                                st.session_state[edit_key] = False
                                st.success(t("Property updated."))
                                st.rerun()
                        if cancel:
                            st.session_state[edit_key] = False
                            st.rerun()

with tab2:
    properties = list_properties(account_id=account_id)
    if not properties:
        empty_state(t("Add a property first before creating units."), icon="🏢")
    else:
        section_label(t("Add a unit"))
        with st.form("add_unit_form", clear_on_submit=True):
            prop_options = {p["name"]: p["id"] for p in properties}
            prop_name = st.selectbox(t("Property*"), list(prop_options.keys()))
            unit_name = st.text_input(t("Unit name/number*"))
            monthly_rent = st.number_input(f"{t('Monthly rent')} ({currency})*", min_value=0.0, step=10000.0)
            water_rate = st.number_input(f"{t('Water rate per month')} ({currency})", min_value=0.0, step=1000.0)
            submitted = st.form_submit_button(t("Add unit"))
            if submitted:
                if not require_active_subscription():
                    pass
                elif not unit_name.strip():
                    st.error(t("Unit name is required."))
                else:
                    add_unit(prop_options[prop_name], unit_name.strip(), monthly_rent, water_rate)
                    st.success(t("Added unit") + f" '{unit_name}'.")
                    st.rerun()

        section_label(t("All units"))
        units = list_units(account_id=account_id)
        if not units:
            empty_state(t("No units yet. Add one above."), icon="🔑")
        else:
            import pandas as pd
            df = pd.DataFrame([{
                t("Property"): u["property_name"],
                t("Unit"): u["unit_name"],
                f"{t('Rent')} ({currency})": f"{u['monthly_rent']:,.0f}",
                f"{t('Water rate')} ({currency})": f"{u['water_rate']:,.0f}",
                t("Status"): u["status"],
            } for u in units])
            st.dataframe(df, use_container_width=True, hide_index=True)

            section_label(t("Edit a unit"))
            unit_options = {f"{u['property_name']} — {u['unit_name']}": u["id"] for u in units}
            unit_to_edit_label = st.selectbox(t("Select unit to edit"), list(unit_options.keys()), key="edit_unit_select")
            unit_to_edit = get_unit(unit_options[unit_to_edit_label])

            with st.form("edit_unit_form"):
                new_unit_name = st.text_input(t("Unit name/number"), value=unit_to_edit["unit_name"])
                new_rent = st.number_input(f"{t('Monthly rent')} ({currency})", min_value=0.0,
                                            value=float(unit_to_edit["monthly_rent"]), step=10000.0)
                new_water = st.number_input(f"{t('Water rate')} ({currency})", min_value=0.0,
                                             value=float(unit_to_edit["water_rate"]), step=1000.0)
                save_unit = st.form_submit_button(t("Save changes"))
                if save_unit:
                    if not require_active_subscription():
                        pass
                    elif not new_unit_name.strip():
                        st.error(t("Unit name is required."))
                    else:
                        update_unit(unit_to_edit["id"], new_unit_name.strip(), new_rent, new_water)
                        st.success(t("Unit updated."))
                        st.rerun()

            section_label(t("Delete a unit"))
            unit_to_delete_label = st.selectbox(t("Select unit to delete"), list(unit_options.keys()), key="delete_unit_select")
            if st.button(t("Delete selected unit")):
                if require_active_subscription():
                    delete_unit(unit_options[unit_to_delete_label])
                    st.warning(t("Unit deleted."))
                    st.rerun()
