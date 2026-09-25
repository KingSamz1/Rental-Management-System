import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_tenants, generate_charge, generate_charges_for_all_active,
    list_charges, current_period, period_label,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Rent", page_icon="💰", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()

currency = (get_account(account_id) or {}).get("currency", "ZAR")

page_header("Monthly Rent Management", icon="💰")
subscription_banner()
st.write("")

section_label("Generate this month's charges")
period = st.text_input("Billing period (YYYY-MM)", value=current_period())
st.caption(f"Billing for: {period_label(period)}")

col1, col2 = st.columns(2)
with col1:
    if st.button("Generate rent for ALL active tenants", type="primary"):
        if require_active_subscription():
            created = generate_charges_for_all_active(period)
            st.success(f"Created {created} new rent charge(s) for {period_label(period)}. "
                        f"(Tenants who already had a charge for this period were skipped.)")

with col2:
    st.caption(
        "This creates one rent+water charge per active tenant for the period, using "
        "their unit's current monthly rent and water rate. Safe to click multiple times — "
        "it won't duplicate existing charges."
    )

st.divider()
section_label("Add or adjust a single tenant's charge")
tenants = list_tenants(status="active", account_id=account_id)
if not tenants:
    empty_state("No active tenants yet.", icon="👤")
else:
    with st.form("single_charge_form"):
        tenant_options = {f"{t['full_name']} — {t['property_name']}/{t['unit_name']}": t for t in tenants}
        tenant_label = st.selectbox("Tenant*", list(tenant_options.keys()))
        selected = tenant_options[tenant_label]
        charge_period = st.text_input("Period (YYYY-MM)*", value=current_period(), key="single_period")
        rent_amount = st.number_input(f"Rent amount ({currency})", min_value=0.0,
                                       value=float(selected["monthly_rent"]), step=10000.0)
        water_amount = st.number_input(f"Water amount ({currency})", min_value=0.0,
                                        value=float(selected["water_rate"]), step=1000.0)
        other_amount = st.number_input(f"Other charges ({currency})", min_value=0.0, step=1000.0)
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Create/update charge")
        if submitted:
            if require_active_subscription():
                generate_charge(selected["id"], charge_period, rent_amount, water_amount, other_amount, note)
                st.success(f"Charge saved for {selected['full_name']} — {period_label(charge_period)}.")
                st.rerun()

st.divider()
section_label("Charge history")
tenant_filter_options = {"All tenants": None}
tenant_filter_options.update({f"{t['full_name']} — {t['unit_name']}": t["id"] for t in list_tenants(account_id=account_id)})
filter_label = st.selectbox("Filter by tenant", list(tenant_filter_options.keys()))
charges = list_charges(tenant_id=tenant_filter_options[filter_label])

if not charges:
    empty_state("No charges recorded yet.", icon="🧾")
else:
    import pandas as pd
    from utils.logic import get_tenant
    rows = []
    for c in charges:
        t = get_tenant(c["tenant_id"])
        rows.append({
            "Period": period_label(c["period"]),
            "Tenant": t["full_name"] if t else "—",
            "Unit": t["unit_name"] if t else "—",
            f"Rent ({currency})": f"{c['rent_amount']:,.0f}",
            f"Water ({currency})": f"{c['water_amount']:,.0f}",
            f"Other ({currency})": f"{c['other_amount']:,.0f}",
            f"Total ({currency})": f"{c['rent_amount'] + c['water_amount'] + c['other_amount']:,.0f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
