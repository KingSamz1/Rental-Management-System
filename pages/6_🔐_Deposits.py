import streamlit as st
from datetime import date
from utils.db import init_db, get_account, get_conn
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import list_tenants, add_deposit, list_deposits
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Deposits", page_icon="🔐", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()
account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Security Deposits"), icon="🔐")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs([t("Add deposit"), t("All deposits")])

with tab1:
    tenants = list_tenants(status="active", account_id=account_id)
    if not tenants:
        empty_state(t("No active tenants found."), icon="👤")
    else:
        with st.form("add_deposit_form", clear_on_submit=True):
            tenant_options = {f"{t['full_name']} — {t['property_name']} / {t['unit_name']}": t["id"] for t in tenants}
            tenant_label = st.selectbox(t("Tenant*"), list(tenant_options.keys()))
            amount = st.number_input(f"{t('Deposit amount')} ({currency})*", min_value=0.0, step=10000.0)
            date_received = st.date_input(t("Date received"), value=date.today())
            note = st.text_input(t("Note (optional)"))
            submitted = st.form_submit_button(t("Record deposit"))
            if submitted:
                if not require_active_subscription():
                    pass
                elif amount <= 0:
                    st.error(t("Amount must be greater than zero."))
                else:
                    add_deposit(
                        tenant_id=tenant_options[tenant_label],
                        amount=amount,
                        date_received=date_received.isoformat(),
                        note=note,
                    )
                    st.success(f"✅ {t('Deposit recorded.')}")
                    st.rerun()

with tab2:
    all_tenants = list_tenants(status=None, account_id=account_id)
    if not all_tenants:
        empty_state(t("No tenants found."), icon="👤")
    else:
        for ten in all_tenants:
            deposits = list_deposits(ten["id"])
            if deposits:
                with st.expander(f"{ten['full_name']} — {ten['property_name']} / {ten['unit_name']}"):
                    for dep in deposits:
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        col1.write(f"**{currency} {dep['amount']:,.0f}**")
                        col2.write(dep["date_received"])
                        col3.write(dep.get("note") or "—")
                        status = dep.get("status", "held")
                        col4.write(f"🟢 {t('held')}" if status == "held" else f"🔴 {t('refunded')}")
                        if status == "held":
                            if st.button(t("Mark as refunded"), key=f"refund_{dep['id']}"):
                                if require_active_subscription():
                                    with get_conn() as conn:
                                        conn.execute("UPDATE deposits SET status='refunded' WHERE id=?", (dep["id"],))
                                    st.success(t("Deposit marked as refunded."))
                                    st.rerun()
                        st.divider()
