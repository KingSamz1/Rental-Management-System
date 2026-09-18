import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
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

page_header("Advance Rent", icon="📅")
subscription_banner()

st.caption(
    "Advance rent is tracked here as a record of prepayment. It is not automatically "
    "netted against future monthly charges — when the covered month comes around, record "
    "the actual payment against that month's charge on the Payments page, referencing this "
    "advance in the note if useful."
)

tenants = list_tenants(status="active", account_id=account_id)

if not tenants:
    empty_state("No active tenants yet.", icon="👤")
else:
    section_label("Record advance rent")
    with st.form("advance_form", clear_on_submit=True):
        tenant_options = {f"{t['full_name']} — {t['property_name']}/{t['unit_name']}": t["id"] for t in tenants}
        tenant_label = st.selectbox("Tenant*", list(tenant_options.keys()))
        amount = st.number_input(f"Amount ({currency})*", min_value=0.0, step=10000.0)
        months_covered = st.number_input("Number of months covered*", min_value=1, step=1, value=1)
        date_received = st.date_input("Date received", value=date.today())
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Record advance rent")
        if submitted:
            if not require_active_subscription():
                pass
            elif amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                add_advance_rent(tenant_options[tenant_label], amount, int(months_covered),
                                  date_received.isoformat(), note.strip())
                st.success("Advance rent recorded.")
                st.rerun()

st.divider()
section_label("Advance rent history")
records = list_advance_rent()
if not records:
    empty_state("No advance rent recorded yet.", icon="📅")
else:
    import pandas as pd
    df = pd.DataFrame([{
        "Tenant": r["full_name"],
        f"Amount ({currency})": f"{r['amount']:,.0f}",
        "Months covered": r["months_covered"],
        "Date received": r["date_received"],
        "Note": r["note"] or "",
    } for r in records])
    st.dataframe(df, use_container_width=True, hide_index=True)
