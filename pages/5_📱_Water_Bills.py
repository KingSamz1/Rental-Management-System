import streamlit as st
from utils.db import init_db, get_setting, get_conn
from utils.auth import check_login, logout_button
from utils.logic import list_units, list_tenants
from utils.theme import apply_theme, page_header, empty_state, section_label

st.set_page_config(page_title="Water Bills", page_icon="📱", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

currency = get_setting("currency", "UGX")

page_header("Water Bills", icon="📱")
st.caption(
    "Water rates are set per unit (see Properties & Units) and pulled in automatically "
    "when you generate monthly rent charges. You can also override the water amount for "
    "a specific month on the Rent page. This page gives a quick overview of current water "
    "rates across your units."
)
st.write("")

units = list_units()
if not units:
    empty_state("No units yet.", icon="💧")
else:
    import pandas as pd
    df = pd.DataFrame([{
        "Property": u["property_name"],
        "Unit": u["unit_name"],
        f"Water rate ({currency}/month)": f"{u['water_rate']:,.0f}",
        "Status": u["status"],
    } for u in units])
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
section_label("Update a unit's water rate")

if units:
    unit_options = {f"{u['property_name']} — {u['unit_name']}": u for u in units}
    unit_label = st.selectbox("Unit", list(unit_options.keys()))
    selected = unit_options[unit_label]
    new_rate = st.number_input(f"New water rate ({currency}/month)", min_value=0.0,
                                value=float(selected["water_rate"]), step=1000.0)
    if st.button("Update water rate"):
        with get_conn() as conn:
            conn.execute("UPDATE units SET water_rate = ? WHERE id = ?", (new_rate, selected["id"]))
        st.success(f"Water rate for {unit_label} updated to {currency} {new_rate:,.0f}.")
        st.rerun()
