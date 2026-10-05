import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import (
    list_tenants, all_tenant_balances, list_payments,
    current_period, period_label, list_charges,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Reports"), icon="📊")
subscription_banner()
st.write("")

period = current_period()

tab1, tab2, tab3 = st.tabs([t("Balances"), t("Monthly income"), t("Tenant history")])

with tab1:
    section_label(t("All tenant balances"))
    balances = all_tenant_balances(account_id=account_id)
    if not balances:
        empty_state(t("No tenants found."), icon="👤")
    else:
        import pandas as pd
        total_owed   = sum(b["balance"] for b in balances if b["balance"] > 0)
        total_credit = sum(abs(b["balance"]) for b in balances if b["balance"] < 0)
        col1, col2 = st.columns(2)
        col1.metric(t("Total outstanding"), f"{currency} {total_owed:,.0f}")
        col2.metric(t("Total credit"), f"{currency} {total_credit:,.0f}")
        st.write("")
        df = pd.DataFrame([{
            t("Tenant"): b["full_name"],
            t("Property"): b["property_name"],
            t("Unit"): b["unit_name"],
            t("Status"): b["balance_status"],
            f"{t('Balance')} ({currency})": f"{b['balance']:,.0f}",
        } for b in balances])
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    section_label(t("Monthly income"))
    view_period = st.text_input(t("Period (YYYY-MM)"), value=period)
    payments = list_payments(account_id=account_id, limit=500)
    month_payments = [p for p in payments if p["payment_date"].startswith(view_period)]
    if not month_payments:
        empty_state(t("No payments found for this period."), icon="💳")
    else:
        total = sum(p["amount"] for p in month_payments)
        st.metric(f"{t('Total collected')} — {period_label(view_period)}", f"{currency} {total:,.0f}")
        import pandas as pd
        df = pd.DataFrame([{
            t("Date"): p["payment_date"],
            t("Tenant"): p["full_name"],
            t("Property"): p["property_name"],
            t("Unit"): p["unit_name"],
            f"{t('Amount')} ({currency})": f"{p['amount']:,.0f}",
            t("Method"): p["method"],
            t("Type"): p["payment_type"],
        } for p in month_payments])
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    section_label(t("Tenant payment history"))
    tenants = list_tenants(status=None, account_id=account_id)
    if not tenants:
        empty_state(t("No tenants found."), icon="👤")
    else:
        tenant_options = {f"{t['full_name']} — {t['property_name']} / {t['unit_name']}": t["id"] for t in tenants}
        selected_label = st.selectbox(t("Select tenant"), list(tenant_options.keys()))
        tenant_id = tenant_options[selected_label]
        payments = list_payments(tenant_id=tenant_id, limit=200)
        if not payments:
            empty_state(t("No payments recorded for this tenant."), icon="💳")
        else:
            total = sum(p["amount"] for p in payments)
            st.metric(t("Total paid (all time)"), f"{currency} {total:,.0f}")
            import pandas as pd
            df = pd.DataFrame([{
                t("Date"): p["payment_date"],
                f"{t('Amount')} ({currency})": f"{p['amount']:,.0f}",
                t("Method"): p["method"],
                t("Type"): p["payment_type"],
                t("Note"): p.get("note") or "",
            } for p in payments])
            st.dataframe(df, use_container_width=True, hide_index=True)
