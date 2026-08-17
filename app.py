import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
from utils.db import init_db, get_setting, set_setting
from utils.auth import check_login, logout_button
from utils.logic import portfolio_summary, all_tenant_balances, current_period, period_label
from utils.theme import apply_theme, page_header, section_label, empty_state, subscription_banner, metric_row, status_pill

st.set_page_config(page_title="Rental Management", page_icon="🏠", layout="wide")
apply_theme()

init_db()

if not check_login():
    st.stop()

# Seed settings from secrets.toml on first run only (don't overwrite later edits made in Settings page)
if get_setting("business_name") is None:
    try:
        set_setting("business_name", st.secrets["landlord"]["business_name"])
        set_setting("currency", st.secrets["landlord"]["currency"])
        set_setting("business_phone", st.secrets["landlord"]["phone"])
    except Exception:
        set_setting("business_name", "Rental Management")
        set_setting("currency", "UGX")
        set_setting("business_phone", "")

logout_button()

business_name = get_setting("business_name", "Rental Management")
currency = get_setting("currency", "UGX")

page_header(business_name, subtitle=f"Dashboard · {period_label(current_period())}", icon="🏠")
subscription_banner()
st.write("")

summary = portfolio_summary()

metric_row([
    {"label": "Units", "value": f"{summary['total_units']} ({summary['occupied_units']} occupied)", "tone": "neutral"},
    {"label": "Vacant units", "value": summary["vacant_units"], "tone": "neutral"},
    {"label": "Active tenants", "value": summary["active_tenants"], "tone": "neutral"},
    {"label": "Collected this month", "value": f"{currency} {summary['collected_this_month']:,.0f}", "tone": "accent"},
])
metric_row([
    {"label": "Total outstanding", "value": f"{currency} {summary['total_outstanding']:,.0f}", "tone": "danger"},
    {"label": "Total tenant credit", "value": f"{currency} {summary['total_credit']:,.0f}", "tone": "accent"},
])

st.divider()
section_label("Tenant balances")

balances = all_tenant_balances()

if not balances:
    empty_state("No tenants yet. Add properties, units, and tenants from the sidebar to get started.", icon="🏘️")
else:
    from utils.theme import colors
    c = colors()
    pill_tone = {"owing": "danger", "credit": "accent", "settled": "neutral"}
    rows_html = ""
    for b in balances:
        tone = pill_tone.get(b["balance_status"], "neutral")
        pill = status_pill(f"{b['balance_status'].title()} · {currency} {b['balance']:,.0f}", tone)
        rows_html += (
            f'<div style="display:flex; justify-content:space-between; align-items:center; '
            f'padding:10px 0; border-bottom:1px solid {c["BORDER"]};">'
            f'<div>'
            f'<div style="font-size:14px; font-weight:500;">{b["full_name"]}</div>'
            f'<div style="font-size:12px; color:{c["TEXT_MUTED"]};">{b["property_name"]} — {b["unit_name"]}</div>'
            f'</div>'
            f'{pill}'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:0.5rem 1.2rem;">{rows_html}</div>',
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    "Use the pages in the sidebar to manage properties, tenants, rent, payments, "
    "water bills, deposits, advance rent, reminders, and reports."
)
