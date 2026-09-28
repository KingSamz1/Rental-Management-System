import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import (
    list_tenants, current_period, period_label, generate_rent_charges,
    list_charges, tenant_balance,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Rent", page_icon="💰", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Rent Charges"), icon="💰")
subscription_banner()
st.write("")

period = current_period()

section_label(t("Generate rent charges"))
st.caption(t("This creates a rent charge for each active tenant for the selected month. Safe to run multiple times — it won't create duplicates."))

with st.form("generate_rent_form"):
    selected_period = st.text_input(t("Period (YYYY-MM)"), value=period)
    submitted = st.form_submit_button(t("Generate charges"), type="primary")
    if submitted:
        if not require_active_subscription():
            pass
        else:
            count = generate_rent_charges(selected_period, account_id=account_id)
            st.success(f"{t('Generated')} {count} {t('charge(s) for')} {period_label(selected_period)}.")

st.divider()
section_label(t("Charges overview"))

tenants = list_tenants(status="active", account_id=account_id)
if not tenants:
    empty_state(t("No active tenants found."), icon="👤")
else:
    view_period = st.text_input(t("View period (YYYY-MM)"), value=period, key="view_period")
    for ten in tenants:
        charges = list_charges(ten["id"], period=view_period)
        bal = tenant_balance(ten["id"])
        charge_total = sum(c["rent_amount"] + c["water_amount"] + c["other_amount"] for c in charges)
        status_icon = "✅" if bal["balance"] <= 0 else "⚠️"
        with st.expander(f"{status_icon} {ten['full_name']} — {ten['property_name']} / {ten['unit_name']}"):
            if not charges:
                st.info(t("No charges generated for this period yet."))
            else:
                for c in charges:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(t("Rent"), f"{currency} {c['rent_amount']:,.0f}")
                    col2.metric(t("Water"), f"{currency} {c['water_amount']:,.0f}")
                    col3.metric(t("Other"), f"{currency} {c['other_amount']:,.0f}")
                    col4.metric(t("Total"), f"{currency} {charge_total:,.0f}")
                    if c.get("note"):
                        st.caption(f"{t('Note')}: {c['note']}")
            st.write(f"**{t('Running balance')}:** {currency} {bal['balance']:,.0f} ({t(bal['balance_status'].title())})")
