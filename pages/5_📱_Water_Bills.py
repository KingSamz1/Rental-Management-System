import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import (
    list_tenants, current_period, period_label, list_charges,
    add_water_charge, tenant_balance,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Water Bills", page_icon="📱", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Water Bills"), icon="💧")
subscription_banner()
st.write("")

period = current_period()

section_label(t("Add water charge"))
st.caption(t("Add a water bill to a tenant's existing rent charge for the selected period."))

tenants = list_tenants(status="active", account_id=account_id)
if not tenants:
    empty_state(t("No active tenants found."), icon="👤")
else:
    with st.form("water_charge_form", clear_on_submit=True):
        tenant_options = {f"{t['full_name']} — {t['property_name']} / {t['unit_name']}": t["id"] for t in tenants}
        tenant_label = st.selectbox(t("Tenant*"), list(tenant_options.keys()))
        tenant_id = tenant_options[tenant_label]
        selected_period = st.text_input(t("Period (YYYY-MM)"), value=period)
        units_used = st.number_input(t("Units of water used (m³)"), min_value=0.0, step=0.5)
        rate_override = st.number_input(
            f"{t('Rate per unit')} ({currency}) — {t('leave 0 to use unit default')}",
            min_value=0.0, step=500.0,
        )
        note = st.text_input(t("Note (optional)"))
        submitted = st.form_submit_button(t("Add water charge"))
        if submitted:
            if not require_active_subscription():
                pass
            elif units_used <= 0:
                st.error(t("Units used must be greater than zero."))
            else:
                result = add_water_charge(
                    tenant_id=tenant_id,
                    period=selected_period,
                    units_used=units_used,
                    rate_override=rate_override if rate_override > 0 else None,
                    note=note,
                )
                if result:
                    st.success(f"✅ {t('Water charge added.')}")
                else:
                    st.error(t("Could not add water charge. Make sure a rent charge exists for this period first."))
                st.rerun()

    st.divider()
    section_label(t("Water charges by tenant"))
    view_period = st.text_input(t("View period (YYYY-MM)"), value=period, key="view_period_water")
    for ten in tenants:
        charges = list_charges(ten["id"], period=view_period)
        water_charges = [c for c in charges if c["water_amount"] > 0]
        if water_charges:
            with st.expander(f"{ten['full_name']} — {ten['property_name']} / {ten['unit_name']}"):
                for c in water_charges:
                    st.write(f"**{t('Period')}:** {c['period']}")
                    st.write(f"**{t('Water amount')}:** {currency} {c['water_amount']:,.0f}")
                    if c.get("note"):
                        st.caption(f"{t('Note')}: {c['note']}")
