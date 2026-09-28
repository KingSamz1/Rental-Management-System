import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import (
    list_tenants, list_charges, record_payment, list_payments,
    generate_receipt, tenant_balance,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Payments", page_icon="💳", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account = get_account(account_id) or {}
currency = account.get("currency", "UGX")
business_name = account.get("business_name", "My Rentals")

page_header(t("Payments"), icon="💳")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs([t("Record payment"), t("Payment history")])

with tab1:
    tenants = list_tenants(status="active", account_id=account_id)
    if not tenants:
        empty_state(t("No active tenants. Add tenants first."), icon="👤")
    else:
        with st.form("record_payment_form", clear_on_submit=True):
            tenant_options = {f"{t['full_name']} — {t['property_name']} / {t['unit_name']}": t["id"] for t in tenants}
            tenant_label = st.selectbox(t("Tenant*"), list(tenant_options.keys()))
            tenant_id = tenant_options[tenant_label]

            charges = list_charges(tenant_id)
            charge_options = {"— " + t("No specific charge (general payment)") + " —": None}
            for c in charges:
                total = c["rent_amount"] + c["water_amount"] + c["other_amount"]
                charge_options[f"{c['period']} — {currency} {total:,.0f}"] = c["id"]

            charge_label = st.selectbox(t("Apply to charge (optional)"), list(charge_options.keys()))
            amount = st.number_input(f"{t('Amount')} ({currency})*", min_value=0.0, step=10000.0)
            payment_date = st.date_input(t("Payment date"), value=date.today())
            method = st.selectbox(t("Method"), ["cash", "MoMo", "bank transfer", "cheque", "other"])
            momo_ref = ""
            momo_provider = ""
            if method == "MoMo":
                momo_provider = st.selectbox(t("MoMo provider"), ["MTN MoMo", "Airtel Money", "Other"])
                momo_ref = st.text_input(t("MoMo transaction reference"))
            payment_type = st.selectbox(t("Payment type"), ["rent", "water", "deposit", "advance_rent", "other"])
            note = st.text_input(t("Note (optional)"))
            submitted = st.form_submit_button(t("Record payment"), type="primary")

            if submitted:
                if not require_active_subscription():
                    pass
                elif amount <= 0:
                    st.error(t("Amount must be greater than zero."))
                else:
                    payment_id = record_payment(
                        tenant_id=tenant_id,
                        charge_id=charge_options[charge_label],
                        amount=amount,
                        payment_date=payment_date.isoformat(),
                        method=method,
                        momo_reference=momo_ref,
                        momo_provider=momo_provider,
                        payment_type=payment_type,
                        note=note,
                    )
                    receipt_path, receipt_number = generate_receipt(
                        payment_id=payment_id,
                        business_name=business_name,
                        currency=currency,
                    )
                    st.success(f"✅ {t('Payment recorded!')} {t('Receipt')}: {receipt_number}")
                    with open(receipt_path, "rb") as f:
                        st.download_button(
                            f"📄 {t('Download receipt')} {receipt_number}",
                            f, file_name=f"receipt_{receipt_number}.pdf",
                            mime="application/pdf",
                        )
                    st.rerun()

with tab2:
    section_label(t("All payments"))
    payments = list_payments(account_id=account_id, limit=100)
    if not payments:
        empty_state(t("No payments recorded yet."), icon="💳")
    else:
        import pandas as pd
        df = pd.DataFrame([{
            t("Date"): p["payment_date"],
            t("Tenant"): p["full_name"],
            t("Property"): p["property_name"],
            t("Unit"): p["unit_name"],
            f"{t('Amount')} ({currency})": f"{p['amount']:,.0f}",
            t("Method"): p["method"],
            t("Type"): p["payment_type"],
            t("Note"): p.get("note") or "",
        } for p in payments])
        st.dataframe(df, use_container_width=True, hide_index=True)
