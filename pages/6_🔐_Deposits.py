import streamlit as st
from datetime import date
from utils.db import init_db, get_setting, get_conn, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import list_tenants, add_deposit, list_deposits
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Deposits", page_icon="🔐", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()

currency = (get_account(account_id) or {}).get("currency", "ZAR")

page_header("Security Deposits", icon="🔐")
subscription_banner()
st.write("")

tenants = list_tenants(status="active", account_id=account_id)

if not tenants:
    empty_state("No active tenants yet.", icon="👤")
else:
    section_label("Record a deposit")
    with st.form("deposit_form", clear_on_submit=True):
        tenant_options = {f"{t['full_name']} — {t['property_name']}/{t['unit_name']}": t["id"] for t in tenants}
        tenant_label = st.selectbox("Tenant*", list(tenant_options.keys()))
        amount = st.number_input(f"Deposit amount ({currency})*", min_value=0.0, step=10000.0)
        date_received = st.date_input("Date received", value=date.today())
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Record deposit")
        if submitted:
            if not require_active_subscription():
                pass
            elif amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                add_deposit(tenant_options[tenant_label], amount, date_received.isoformat(), note.strip())
                st.success("Deposit recorded.")
                st.rerun()

st.divider()
section_label("All deposits")
deposits = list_deposits()
if not deposits:
    empty_state("No deposits recorded yet.", icon="🔐")
else:
    import pandas as pd
    df = pd.DataFrame([{
        "Tenant": d["full_name"],
        f"Amount ({currency})": f"{d['amount']:,.0f}",
        "Date received": d["date_received"],
        "Status": d["status"],
        "Note": d["note"] or "",
        "_id": d["id"],
    } for d in deposits])
    st.dataframe(df.drop(columns=["_id"]), use_container_width=True, hide_index=True)

    section_label("Update deposit status")
    dep_options = {f"{d['full_name']} — {currency} {d['amount']:,.0f} ({d['date_received']})": d["id"] for d in deposits}
    dep_label = st.selectbox("Select deposit", list(dep_options.keys()))
    new_status = st.selectbox("New status", ["held", "refunded", "forfeited"])
    if st.button("Update status"):
        with get_conn() as conn:
            conn.execute("UPDATE deposits SET status = ? WHERE id = ?", (new_status, dep_options[dep_label]))
        st.success("Deposit status updated.")
        st.rerun()
