import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import list_tenants, add_advance_rent, list_advance_rent
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Advance Rent", page_icon="📅", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()
account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Advance Rent"), icon="📅")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs([t("Record advance rent"), t("All advance rent")])

with tab1:
    tenants = list_tenants(status="active", account_id=account_id)
    if not tenants:
        empty_state(t("No active tenants found."), icon="👤")
    else:
        with st.form("advance_rent_form", clear_on_submit=True):
            tenant_options = {f"{t['full_name']} — {t['property_name']} / {t['unit_name']}": t["id"] for t in tenants}
            tenant_label = st.selectbox(t("Tenant*"), list(tenant_options.keys()))
            amount = st.number_input(f"{t('Amount received')} ({currency})*", min_value=0.0, step=10000.0)
            months_covered = st.number_input(t("Months covered*"), min_value=1, step=1, value=1)
            date_received = st.date_input(t("Date received"), value=date.today())
            note = st.text_input(t("Note (optional)"))
            submitted = st.form_submit_button(t("Record advance rent"))
            if submitted:
                if not require_active_subscription():
                    pass
                elif amount <= 0:
                    st.error(t("Amount must be greater than zero."))
                else:
                    add_advance_rent(
                        tenant_id=tenant_options[tenant_label],
                        amount=amount,
                        months_covered=months_covered,
                        date_received=date_received.isoformat(),
                        note=note,
                    )
                    st.success(f"✅ {t('Advance rent recorded.')}")
                    st.rerun()

with tab2:
    all_tenants = list_tenants(status=None, account_id=account_id)
    if not all_tenants:
        empty_state(t("No tenants found."), icon="👤")
    else:
        for ten in all_tenants:
            advances = list_advance_rent(ten["id"])
            if advances:
                with st.expander(f"{ten['full_name']} — {ten['property_name']} / {ten['unit_name']}"):
                    for adv in advances:
                        col1, col2, col3 = st.columns(3)
                        col1.metric(f"{t('Amount')} ({currency})", f"{adv['amount']:,.0f}")
                        col2.metric(t("Months covered"), adv["months_covered"])
                        col3.write(f"**{t('Date')}:** {adv['date_received']}")
                        if adv.get("note"):
                            st.caption(f"{t('Note')}: {adv['note']}")
                        st.divider()
