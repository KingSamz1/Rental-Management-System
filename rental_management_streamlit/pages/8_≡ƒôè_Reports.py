import streamlit as st
import pandas as pd
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    all_tenant_balances, list_payments, list_charges, list_deposits,
    list_advance_rent, current_period, period_label,
)
from utils.theme import apply_theme, page_header, empty_state

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()

currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header("Reports", icon="📊")
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(["Balances", "Payments", "Charges", "Deposits & Advance"])

with tab1:
    st.subheader("Tenant balances")
    balances = all_tenant_balances()
    if not balances:
        empty_state("No data yet.", icon="📊")
    else:
        df = pd.DataFrame([{
            "Tenant": b["full_name"],
            "Property": b["property_name"],
            "Unit": b["unit_name"],
            "Tenant status": b["status"],
            "Total charged": b["total_charged"],
            "Total paid": b["total_paid"],
            "Balance": b["balance"],
            "Balance status": b["balance_status"],
        } for b in balances])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download balances CSV", df.to_csv(index=False).encode("utf-8"),
            file_name="tenant_balances.csv", mime="text/csv",
        )

with tab2:
    st.subheader("All payments")
    payments = list_payments()
    if not payments:
        empty_state("No data yet.", icon="📊")
    else:
        df = pd.DataFrame([{
            "Date": p["payment_date"],
            "Tenant": p["full_name"],
            "Property": p["property_name"],
            "Unit": p["unit_name"],
            "Type": p["payment_type"],
            "Amount": p["amount"],
            "Method": p["method"],
            "MoMo Provider": p["momo_provider"] or "",
            "MoMo Reference": p["momo_reference"] or "",
            "Note": p["note"] or "",
        } for p in payments])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download payments CSV", df.to_csv(index=False).encode("utf-8"),
            file_name="payments.csv", mime="text/csv",
        )
        st.metric(f"Total collected all-time ({currency})", f"{df['Amount'].sum():,.0f}")

with tab3:
    st.subheader("All rent charges")
    charges = list_charges()
    if not charges:
        empty_state("No data yet.", icon="📊")
    else:
        from utils.logic import get_tenant
        rows = []
        for c in charges:
            t = get_tenant(c["tenant_id"])
            rows.append({
                "Period": c["period"],
                "Tenant": t["full_name"] if t else "—",
                "Rent": c["rent_amount"],
                "Water": c["water_amount"],
                "Other": c["other_amount"],
                "Total": c["rent_amount"] + c["water_amount"] + c["other_amount"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download charges CSV", df.to_csv(index=False).encode("utf-8"),
            file_name="rent_charges.csv", mime="text/csv",
        )

with tab4:
    st.subheader("Deposits")
    deposits = list_deposits()
    if deposits:
        df_dep = pd.DataFrame([{
            "Tenant": d["full_name"], "Amount": d["amount"],
            "Date received": d["date_received"], "Status": d["status"], "Note": d["note"] or "",
        } for d in deposits])
        st.dataframe(df_dep, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download deposits CSV", df_dep.to_csv(index=False).encode("utf-8"),
            file_name="deposits.csv", mime="text/csv", key="dep_csv",
        )
    else:
        empty_state("No deposits yet.", icon="🔐")

    st.subheader("Advance rent")
    advances = list_advance_rent()
    if advances:
        df_adv = pd.DataFrame([{
            "Tenant": a["full_name"], "Amount": a["amount"], "Months covered": a["months_covered"],
            "Date received": a["date_received"], "Note": a["note"] or "",
        } for a in advances])
        st.dataframe(df_adv, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download advance rent CSV", df_adv.to_csv(index=False).encode("utf-8"),
            file_name="advance_rent.csv", mime="text/csv", key="adv_csv",
        )
    else:
        empty_state("No advance rent yet.", icon="📅")
