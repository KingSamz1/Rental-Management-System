import streamlit as st
from utils.db import init_db, get_account, update_account_settings
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import portfolio_summary, all_tenant_balances, current_period, period_label
from utils.theme import apply_theme, page_header, section_label, empty_state, subscription_banner, metric_row, status_pill

st.set_page_config(page_title="LandlordPro", page_icon="🏠", layout="wide")
apply_theme()
init_db()

if not check_login():
    st.stop()

account_id = get_current_account_id()
account = get_account(account_id)

logout_button()

business_name = account["business_name"] if account else "Rental Management"
currency = account["currency"] if account else "UGX"

page_header(business_name, subtitle=f"Dashboard · {period_label(current_period())}", icon="🏠")
subscription_banner()
st.write("")

summary = portfolio_summary(account_id=account_id)

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

# ── About LandlordPro (collapsible — handy for showing a new user or your dad) ──
with st.expander("ℹ️ About LandlordPro — what this app does", expanded=False):
    st.markdown(
        """
**LandlordPro** is a simple, all-in-one property management tool built for landlords.
Instead of juggling notebooks, WhatsApp messages, and spreadsheets, everything lives in one place.

**What you can do:**

| | Feature | What it means |
|---|---|---|
| 🏢 | **Properties & units** | Add your buildings and individual rental units |
| 👤 | **Tenants** | Store tenant names, contacts, move-in dates, and ID documents |
| 💰 | **Rent & water bills** | Charge rent or water to each tenant every month |
| 💳 | **Payments & receipts** | Record cash or MoMo payments and auto-generate PDF receipts |
| 🔐 | **Deposits & advance rent** | Track security deposits and prepaid months separately |
| 📲 | **WhatsApp reminders** | Send one-tap payment reminders directly to tenants |
| 📊 | **Reports** | See monthly income, outstanding balances, and full payment history |

**Why landlords use it:**
- No more chasing who paid and who hasn't — balances update automatically
- Receipts are generated for you — no printing or manual writing
- Works on any phone or computer, no app to install
- Each landlord has their own private account — your data stays yours
- First month is free, no setup fee
        """,
        unsafe_allow_html=False,
    )

section_label("Tenant balances")

balances = all_tenant_balances(account_id=account_id)

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
st.caption("Use the pages in the sidebar to manage properties, tenants, rent, payments, water bills, deposits, advance rent, reminders, and reports.")
