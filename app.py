import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import portfolio_summary, all_tenant_balances, current_period, period_label, list_payments, list_tenants
from utils.i18n import t, language_selector
from utils.theme import apply_theme, page_header, section_label, empty_state, subscription_banner, metric_row, status_pill, colors

st.set_page_config(page_title="LandlordPro", page_icon="🏠", layout="wide")
apply_theme()
init_db()

if not check_login():
    st.stop()

account_id = get_current_account_id()
account    = get_account(account_id)
logout_button()

business_name = account["business_name"] if account else "Rental Management"
currency      = account["currency"] if account else "UGX"
c = colors()

page_header(business_name, subtitle=f"{t('Dashboard')} · {period_label(current_period())}", icon="🏠")
subscription_banner()
st.write("")

summary = portfolio_summary(account_id=account_id)

# ── Key metrics ───────────────────────────────────────────────────────────────
metric_row([
    {"label": t("Total units"),    "value": str(summary["total_units"]),    "tone": "neutral"},
    {"label": t("Occupied"),       "value": str(summary["occupied_units"]), "tone": "neutral"},
    {"label": t("Vacant"),         "value": str(summary["vacant_units"]),   "tone": "neutral"},
    {"label": t("Active tenants"), "value": str(summary["active_tenants"]), "tone": "neutral"},
])
metric_row([
    {"label": t("Collected this month"),  "value": f"{currency} {summary['collected_this_month']:,.0f}",  "tone": "accent"},
    {"label": t("Total outstanding"),     "value": f"{currency} {summary['total_outstanding']:,.0f}",     "tone": "danger"},
    {"label": t("Total tenant credit"),   "value": f"{currency} {summary['total_credit']:,.0f}",          "tone": "accent"},
])

# ── Quick actions ─────────────────────────────────────────────────────────────
st.write("")
section_label(t("Quick actions"))
qa1, qa2, qa3, qa4, qa5 = st.columns(5)
with qa1:
    if st.button(f"🏢 {t('Add property')}", use_container_width=True):
        st.switch_page("pages/1_🏢_Properties.py")
with qa2:
    if st.button(f"👤 {t('Add tenant')}", use_container_width=True):
        st.switch_page("pages/2_👤_Tenants.py")
with qa3:
    if st.button(f"💳 {t('Record payment')}", use_container_width=True):
        st.switch_page("pages/4_💳_Payments.py")
with qa4:
    if st.button(f"💰 {t('Generate rent')}", use_container_width=True):
        st.switch_page("pages/3_💰_Rent.py")
with qa5:
    if st.button(f"📲 {t('Send reminders')}", use_container_width=True):
        st.switch_page("pages/9_📲_Reminders.py")

st.divider()

# ── Two-column layout: recent payments + tenant balances ──────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    section_label(t("Recent payments"))
    recent = list_payments(account_id=account_id, limit=6)
    if not recent:
        empty_state(t("No payments recorded yet."), icon="💳")
    else:
        rows_html = ""
        for p in recent:
            pill = status_pill(p["method"], "neutral")
            rows_html += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:9px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<div>'
                f'<div style="font-size:13px; font-weight:500;">{p["full_name"]}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]};">{p["payment_date"]} · {p["property_name"]}</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:13px; font-weight:600; color:{c["ACCENT_DARK"]};">{currency} {p["amount"]:,.0f}</div>'
                f'{pill}'
                f'</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.25rem 1.1rem;">{rows_html}</div>',
            unsafe_allow_html=True,
        )

with right:
    section_label(t("Tenant balances"))
    balances = all_tenant_balances(account_id=account_id)
    if not balances:
        empty_state(t("No tenants yet. Add a property and unit first."), icon="🏘️")
    else:
        pill_tone = {"owing": "danger", "credit": "accent", "settled": "neutral"}
        rows_html = ""
        for b in balances:
            tone   = pill_tone.get(b["balance_status"], "neutral")
            status = t(b["balance_status"].title())
            pill   = status_pill(f"{status} · {currency} {abs(b['balance']):,.0f}", tone)
            rows_html += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:9px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<div>'
                f'<div style="font-size:13px; font-weight:500;">{b["full_name"]}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]};">{b["property_name"]} — {b["unit_name"]}</div>'
                f'</div>'
                f'{pill}'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.25rem 1.1rem;">{rows_html}</div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── Foldable "What LandlordPro does" ─────────────────────────────────────────
with st.expander(f"ℹ️ {t('What LandlordPro does')}"):
    features = [
        ("🏢", t("Properties & units"),     t("Add buildings and individual units in seconds.")),
        ("👤", t("Tenant management"),       t("Store contacts, move-in dates, and documents.")),
        ("💰", t("Rent & water bills"),      t("Charge rent or water per tenant each month.")),
        ("💳", t("Payments & receipts"),     t("Record cash or MoMo payments, auto-generate PDF receipts.")),
        ("🔐", t("Deposits & advance rent"), t("Track security deposits and prepaid months separately.")),
        ("📲", t("WhatsApp reminders"),      t("One-tap reminder links sent straight to tenants.")),
        ("📊", t("Reports"),                 t("Monthly income, outstanding balances, and tenant history.")),
    ]
    items_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
        f'<span style="font-size:16px; line-height:1.4;">{icon}</span>'
        f'<div><span style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{title}</span>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">&nbsp;&mdash; {desc}</span></div></div>'
        for icon, title, desc in features
    )
    st.markdown(
        f'<p style="font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55; margin-bottom:10px;">'
        f'{t("A simple, all-in-one tool built for landlords in Africa (and anywhere else). Manage every property, tenant, and payment from one place — no spreadsheets, no paper.")}</p>'
        f'{items_html}'
        f'<p style="margin:10px 0 0; font-size:12px; color:{c["TEXT_MUTED"]}; font-style:italic;">'
        f'{t("First month free · then UGX 30,000/month · No setup fee · Works on any device")}</p>',
        unsafe_allow_html=True,
    )

st.caption(t("LandlordPro · Use the sidebar to manage properties, tenants, rent, payments, water bills, deposits, advance rent, reminders, and reports."))
